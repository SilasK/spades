//***************************************************************************
//* Copyright (c) 2015 Saint-Petersburg State University
//* All Rights Reserved
//* See file LICENSE for details.
//****************************************************************************

#pragma once

#include "pipeline/stage.hpp"
#include "assembly_graph/core/graph.hpp"
#include "assembly_graph/graph_support/coverage_uniformity_analyzer.hpp"

namespace debruijn_graph {

class ChromosomeRemoval : public spades::AssemblyStage {
public:
    ChromosomeRemoval(size_t ext_limit = 0)
            : AssemblyStage("Chromosome Removal", "THIS SHOULD BE REWRITTEN AFTER STAGES REVISITED"), long_component_(), long_vertex_component_(),
              deadends_count_(), ext_limit_(ext_limit), full_name_(std::string("chromosome_removal") + (ext_limit == 0?std::string(""):std::to_string(ext_limit))) {
        this->set_id(full_name_);
    }

    void run(conj_graph_pack &gp, const char *);

private:
    std::string full_name_;
    std::unordered_map <EdgeId, size_t> long_component_;
    std::unordered_map <VertexId, size_t> long_vertex_component_;
    std::unordered_map <EdgeId, size_t> deadends_count_;
    size_t ext_limit_;
    size_t CalculateComponentSize(debruijn_graph::EdgeId e, Graph &g_);

    double RemoveLongGenomicEdges(conj_graph_pack &gp, size_t long_edge_bound, double coverage_limits,
                                  double external_chromosome_coverage = 0);
    void PlasmidSimplify(conj_graph_pack &gp, size_t long_edge_bound,
                                            std::function<void(typename Graph::EdgeId)> removal_handler = 0);
    void CompressAll(Graph &g);

    double RemoveEdgesByList(conj_graph_pack &gp, std::string &s);
    void MetaChromosomeRemoval(conj_graph_pack &gp);
    void RemoveNearlyEverythingByCoverage(conj_graph_pack &gp);
    void RemoveNearlyEverythingByCoverage(conj_graph_pack &gp, size_t limit);

    void CoverageFilter(conj_graph_pack &gp, double coverage_cutoff);


    DECL_LOGGER("ChromosomeRemoval");


    void ReferenceBasedRemoveChromosomal(conj_graph_pack &gp);
};
}
