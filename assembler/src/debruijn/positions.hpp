#pragma once

#include "omni/edges_position_handler.hpp"

namespace debruijn_graph {

template<class Graph, class Mapper>
class PosFiller {
    typedef typename Graph::EdgeId EdgeId;
    const Graph& g_;
    const Mapper& mapper_;
    EdgesPositionHandler<Graph>& edge_pos_;

public:
    PosFiller(const Graph& g, const Mapper& mapper,
            EdgesPositionHandler<Graph>& edge_pos) :
            g_(g), mapper_(mapper), edge_pos_(edge_pos) {

    }

    void Process(const Sequence& s, string name) const {
        //todo stupid conversion!

        return Process(io::SingleRead(name, s.str()));
    }

    void Process(const io::SingleRead& read) const {
        MappingPath<EdgeId> path = mapper_.MapRead(read);
        const string& name = read.name();
        int cur_pos = 0;
        TRACE(
                "Contig " << name << " mapped on " << path.size()
                        << " fragments.");
        for (size_t i = 0; i < path.size(); i++) {
            EdgeId ei = path[i].first;
            MappingRange mr = path[i].second;
            int len = (int) (mr.mapped_range.end_pos - mr.mapped_range.start_pos);
            if (i > 0)
                if (path[i - 1].first != ei)
                    if (g_.EdgeStart(ei) != g_.EdgeEnd(path[i - 1].first)) {
                        TRACE(
                                "Contig " << name
                                        << " mapped on not adjacent edge. Position in contig is "
                                        << path[i - 1].second.initial_range.start_pos
                                                + 1
                                        << "--"
                                        << path[i - 1].second.initial_range.end_pos
                                        << " and "
                                        << mr.initial_range.start_pos + 1
                                        << "--" << mr.initial_range.end_pos);
                    }
            edge_pos_.AddEdgePosition(ei, (int) mr.initial_range.start_pos + 1,
                                      (int) mr.initial_range.end_pos, name,
                                      (int) mr.mapped_range.start_pos + 1,
                                      (int) mr.mapped_range.end_pos);
            cur_pos += len;
        }
    }

private:
    DECL_LOGGER("PosFiller")
    ;
};

template<class Graph, class Mapper>
void FillPos(const Graph& g, const Mapper& mapper,
        EdgesPositionHandler<Graph>& edge_pos,
        io::IReader<io::SingleRead>& stream) {
    PosFiller<Graph, Mapper> filler(g, mapper, edge_pos);
    io::SingleRead read;
    while (!stream.eof()) {
        stream >> read;
        filler.Process(read);
    }
}

template<class gp_t>
void FillPos(gp_t& gp, io::IReader<io::SingleRead>& stream) {
    FillPos(gp.g, *MapperInstance(gp), gp.edge_pos, stream);
}

template<class Graph, class Mapper>
void FillPos(const Graph& g, const Mapper& mapper, EdgesPositionHandler<Graph>& edge_pos, const Sequence& s, const string& name) {
    PosFiller<Graph, Mapper>(g, mapper, edge_pos).Process(s, name);
}

template<class gp_t>
void FillPos(gp_t& gp, const Sequence& s, const string& name) {
    FillPos(gp.g, *MapperInstance(gp), gp.edge_pos, s, name);
}

//deprecated, todo remove usages!!!
template<class gp_t>
void FillPos(gp_t& gp, const string& contig_file, string prefix) {
//  typedef typename gp_t::Graph::EdgeId EdgeId;
    INFO("Threading large contigs");
    io::Reader irs(contig_file);
    while(!irs.eof()) {
        io::SingleRead read;
        irs >> read;
        DEBUG("Contig " << read.name() << ", length: " << read.size());
        if (!read.IsValid()) {
            WARN("Attention: contig " << read.name() << " contains Ns");
            continue;
        }
        Sequence contig = read.sequence();
        if (contig.size() < 1500000) {
            //      continue;
        }
        FillPos(gp, contig, prefix + read.name());
    }
}

template<class gp_t>
void FillPosWithRC(gp_t& gp, const string& contig_file, string prefix) {
//  typedef typename gp_t::Graph::EdgeId EdgeId;
    INFO("Threading large contigs");
    io::EasySplittingReader irs(contig_file, true);
    while(!irs.eof()) {
        io::SingleRead read;
        irs >> read;
        DEBUG("Contig " << read.name() << ", length: " << read.size());
        if (!read.IsValid()) {
            WARN("Attention: contig " << read.name()
                    << " is not valid (possibly contains N's)");
            continue;
        }
        Sequence contig = read.sequence();
        FillPos(gp, contig, prefix + read.name());
    }
}

}
