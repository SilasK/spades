#include "modules/alignment/pacbio/gap_filler.hpp"

namespace sensitive_aligner {


std::string GapFiller::PathToString(const vector<EdgeId>& path) const {
    std::string res = "";
    for (auto iter = path.begin(); iter != path.end(); iter++) {
        size_t len = g_.length(*iter);
        std::string tmp = g_.EdgeNucls(*iter).First(len).str();
        res = res + tmp;
    }
    return res;
}

GapFillerResult GapFiller::BestScoredPathDijkstra(const string &s,
        const GraphPosition &start_pos,
        const GraphPosition &end_pos,
        int path_max_length, int score) const {
    VertexId start_v = g_.EdgeEnd(start_pos.edgeid);
    VertexId end_v = g_.EdgeStart(end_pos.edgeid);
    auto path_searcher_b = omnigraph::DijkstraHelper<debruijn_graph::Graph>::CreateBackwardBoundedDijkstra(g_, path_max_length);
    path_searcher_b.Run(end_v);
    auto path_searcher = omnigraph::DijkstraHelper<debruijn_graph::Graph>::CreateBoundedDijkstra(g_, path_max_length);
    path_searcher.Run(start_v);
    auto reached_vertices_b = path_searcher_b.ProcessedVertices();
    auto reached_vertices = path_searcher.ProcessedVertices();

    std::map<VertexId, size_t> vertex_pathlen;
    for (auto v : reached_vertices_b) {
        if (reached_vertices.count(v) > 0) {
            vertex_pathlen[v] = path_searcher_b.GetDistance(v);
        }
    }
    int s_len = int(s.size());
    int ed_limit = score;
    if (score == std::numeric_limits<int>::max()) {
        ed_limit = min(max(gap_cfg_.ed_lower_bound, s_len / gap_cfg_.max_ed_proportion), gap_cfg_.ed_upper_bound);
    }
    DEBUG(" Dijkstra: String length " << s_len << "  "  << (size_t) s_len <<
          " max-len " << ed_limit << " vertex_num=" << vertex_pathlen.size());
    GapFillerResult dijkstra_res;
    if (vertex_pathlen.size() == 0 ||
            ((size_t) s_len) > pb_config_.max_contigs_gap_length ||
            vertex_pathlen.size() > gap_cfg_.max_vertex_in_gap) {
        DEBUG("Dijkstra won't run: Too big gap or too many paths " << s_len << " " << vertex_pathlen.size());
        if (vertex_pathlen.size() == 0) {
            dijkstra_res.return_code = DijkstraReturnCode::NOT_CONNECTED;
        }
        if (((size_t) s_len) > pb_config_.max_contigs_gap_length) {
            dijkstra_res.return_code += DijkstraReturnCode::TOO_LONG_GAP;
        }
        if (vertex_pathlen.size() > gap_cfg_.max_vertex_in_gap) {
            dijkstra_res.return_code += DijkstraReturnCode::TOO_MANY_VERTICES;
        }
        return dijkstra_res;
    }
    DijkstraGapFiller gap_filler(g_, gap_cfg_, s,
                                 start_pos.edgeid, end_pos.edgeid,
                                 start_pos.position, end_pos.position,
                                 ed_limit, vertex_pathlen);
    gap_filler.CloseGap();
    dijkstra_res.score = gap_filler.edit_distance();
    dijkstra_res.return_code = gap_filler.return_code();
    if (dijkstra_res.score == std::numeric_limits<int>::max()) {
        DEBUG("Dijkstra didn't find anything")
        return dijkstra_res;
    }
    std::vector<EdgeId> ans = gap_filler.path();
    std::vector<EdgeId> short_path(ans.begin() + 1, ans.end() - 1);
    dijkstra_res.intermediate_path = short_path;
    return dijkstra_res;
}

GapFillerResult GapFiller::BestScoredPathBruteForce(const string &seq_string,
        const GraphPosition &start_pos,
        const GraphPosition &end_pos,
        int path_min_length, int path_max_length) const {
    VertexId start_v = g_.EdgeEnd(start_pos.edgeid);
    VertexId end_v = g_.EdgeStart(end_pos.edgeid);
    TRACE(" Traversing tangled region. Start and end vertices resp: " << g_.int_id(start_v) << " " << g_.int_id(end_v));
    omnigraph::PathStorageCallback<debruijn_graph::Graph> callback(g_);
    GapFillerResult bf_res;
    bf_res.return_code = ProcessPaths(g_,
                                      path_min_length, path_max_length,
                                      start_v, end_v,
                                      callback);
    DEBUG("PathProcessor result: " << bf_res.return_code << " limits " << path_min_length << " " << path_max_length);
    std::vector<std::vector<EdgeId> > paths = callback.paths();
    size_t best_path_ind = paths.size();
    int best_score = std::numeric_limits<int>::max();
    if (paths.size() == 0) {
        DEBUG("need to find best scored path between " << paths.size() << " , seq_len " << seq_string.length());
        DEBUG ("no paths");
        return bf_res;
    }
    if (seq_string.length() > pb_config_.max_contigs_gap_length) {
        DEBUG("need to find best scored path between " << paths.size() << " , seq_len " << seq_string.length());
        DEBUG("Gap is too large");
        return bf_res;
    }
    string s_add = g_.EdgeNucls(start_pos.edgeid).Subseq(start_pos.position, g_.length(start_pos.edgeid)).str();
    string e_add = g_.EdgeNucls(end_pos.edgeid).Subseq(0, end_pos.position).str();
    bool additional_debug = (paths.size() > 1 && paths.size() < 10);
    for (size_t i = 0; i < paths.size(); i++) {
        DEBUG("path len " << paths[i].size());
        if (paths[i].size() == 0) {
            DEBUG ("Pathprocessor returns path with size = 0")
        }
        std::string cur_string = s_add + PathToString(paths[i]) + e_add;
        TRACE("cur_string: " << cur_string << "\n seq_string " << seq_string);
        int cur_score = StringDistance(cur_string, seq_string);
        //DEBUG only
        if (additional_debug) {
            TRACE("candidate path number " << i << " , len " << cur_string.length());
            TRACE("graph candidate: " << cur_string);
            TRACE("in pacbio read: " << seq_string);
            for (auto j_iter = paths[i].begin(); j_iter != paths[i].end();
                    ++j_iter) {
                DEBUG(g_.int_id(*j_iter));
            }
            DEBUG("score: " << cur_score);
        }
        if (cur_score < best_score) {
            best_score = cur_score;
            best_path_ind = i;
        }
    }
    TRACE(best_score);
    bf_res.score = best_score;
    if (best_score == std::numeric_limits<int>::max()) {
        if (paths.size() < 10) {
            for (size_t i = 0; i < paths.size(); i++) {
                DEBUG ("failed with strings " << seq_string << " " << s_add + PathToString(paths[i]) + e_add);
            }
        }
        DEBUG (paths.size() << " paths available");
        return bf_res;
    }
    if (additional_debug) {
        TRACE("best score found! Path " << best_path_ind << " score " << best_score);
    }
    bf_res.intermediate_path = paths[best_path_ind];
    return bf_res;
}

GapFillerResult GapFiller::Run(const string &s,
                               const GraphPosition &start_pos,
                               const GraphPosition &end_pos,
                               int path_min_length, int path_max_length) {
    utils::perf_counter pc;
    auto bf_res = BestScoredPathBruteForce(s, start_pos, end_pos, path_min_length, path_max_length);
    double tm1 = pc.time();
    pc.reset();
    if (gap_cfg_.run_dijkstra && bf_res.return_code != 0) {
        auto dijkstra_res = BestScoredPathDijkstra(s, start_pos, end_pos, path_max_length, bf_res.score);
        DEBUG("BruteForce run: return_code=" << bf_res.return_code
              << " score=" << bf_res.score << " time1=" << tm1
              << " Dijkstra run: return_code=" << dijkstra_res.return_code
              << " score=" <<  dijkstra_res.score << " time2=" << pc.time() << " len=" << s.size() << "\n")
        if (dijkstra_res.score != std::numeric_limits<int>::max()) {
            return dijkstra_res;
        }
    }
    if (bf_res.score == std::numeric_limits<int>::max()) {
        bf_res.return_code = DijkstraReturnCode::NO_PATH;
    }
    return bf_res;

}

//////////////////////////////////////////////////////////////////

void EndsFiller::PrepareInitialState(omnigraph::MappingPath<debruijn_graph::EdgeId> &path,
                                     const Sequence &s,
                                     bool forward,
                                     Sequence &ss,
                                     EdgeId &start_e, int &start_pos, int &start_pos_seq) const {
    if (forward) {
        start_e = path.edge_at(path.size() - 1);
        omnigraph::MappingRange mapping = path.mapping_at(path.size() - 1);
        start_pos = (int) mapping.mapped_range.end_pos;
        start_pos_seq = mapping.initial_range.end_pos;
        ss = s.Subseq(mapping.initial_range.end_pos, (int) s.size() );
        DEBUG("Forward e=" << start_e.int_id() << " sp=" << start_pos << " seq_sz" << ss.size())
    } else {
        start_e = g_.conjugate(path.edge_at(0));
        omnigraph::MappingRange mapping = path.mapping_at(0);
        start_pos = min((int) g_.length(start_e), (int) g_.length(start_e) + (int) g_.k() - (int) mapping.mapped_range.start_pos);
        start_pos_seq = 0;
        ss = !s.Subseq(0, mapping.initial_range.start_pos);
        DEBUG("Backward e=" << start_e.int_id() << " sp=" << start_pos << " seq_sz" << ss.size())
    }
}

void EndsFiller::UpdatePath(vector<debruijn_graph::EdgeId> &path,
                            std::vector<EdgeId> &ans,
                            int end_pos, int end_pos_seq, PathRange &range, bool forward) const {
    if (forward) {
        while (end_pos < g_.k() && ans.size() > 0) {
            ans.pop_back();
            end_pos += g_.length(ans[ans.size() - 1]);
        }
        for (int i = 1; i < (int) ans.size(); ++i) {
            path.push_back(ans[i]);
        }
        range.seq_end = end_pos_seq;
        range.edge_end = end_pos;
    } else {
        vector<debruijn_graph::EdgeId> cur_sorted;
        int start = (int) g_.length(ans[ans.size() - 1]) + (int) g_.k() - end_pos;
        int cur_ind = (int) ans.size() - 1;
        while (cur_ind >= 0 && start - (int) g_.length(ans[cur_ind]) > 0) {
            start -= (int) g_.length(ans[cur_ind]);
            cur_ind --;
        }
        if (cur_ind > 0) {
            cur_sorted.push_back(g_.conjugate(ans[cur_ind]) );
        }
        for (int i = cur_ind - 1; i > 0; --i) {
            cur_sorted.push_back(g_.conjugate(ans[i]));
        }
        for (size_t i = 0; i < path.size(); ++i) {
            cur_sorted.push_back(path[i]);
        }
        path = cur_sorted;
        range.seq_start = 0;
        range.edge_start = start;
    }
}

void EndsFiller::Run(omnigraph::MappingPath<debruijn_graph::EdgeId> &bwa_hits,
                     vector<debruijn_graph::EdgeId> &path,
                     const Sequence &s, bool forward, PathRange &range, int &return_code) {
    VERIFY(path.size() > 0);
    Sequence ss;
    int start_pos = -1;
    int start_pos_seq = -1;
    return_code = 0;
    EdgeId start_e = EdgeId();
    PrepareInitialState(bwa_hits, s, forward, ss, start_e, start_pos, start_pos_seq);

    int s_len = int(ss.size());
    int score = min(max(gap_cfg_.ed_lower_bound, s_len / gap_cfg_.max_ed_proportion), gap_cfg_.ed_upper_bound);
    if (s_len > (int) gap_cfg_.max_restorable_end_length) {
        DEBUG("EdgeDijkstra: sequence is too long " << s_len)
        return_code += 1;
        return;
    }
    if (s_len < 1) {
        DEBUG("EdgeDijkstra: sequence is too small " << s_len)
        return_code += 2;
        return;
    }
    DijkstraEndsReconstructor algo(g_, gap_cfg_, ss.str(), start_e, start_pos, score);
    algo.CloseGap();
    score = algo.edit_distance();
    return_code += algo.return_code();
    if (score == std::numeric_limits<int>::max()) {
        DEBUG("EdgeDijkstra didn't find anything edge=" << start_e.int_id()
              << " s_start=" << start_pos << " seq_len=" << ss.size())
        return;
    }
    std::vector<EdgeId> ans = algo.path();
    int end_pos = algo.path_end_position();
    int end_pos_seq = forward ? algo.seq_end_position() + start_pos_seq : 0;
    UpdatePath(path, ans, end_pos, end_pos_seq, range, forward);
}


} // namespace sensitive_aligner