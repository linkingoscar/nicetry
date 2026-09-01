from __future__ import annotations

from app.api.schemas import EmpiricalAnalysisRequest


def build_empirical_analysis_options(request: EmpiricalAnalysisRequest) -> dict[str, object]:
    """Build normalized empirical analysis options dictionary from request DTO."""
    return {
        "procedure": request.procedure,
        "analysisVariableIds": request.analysis_variable_ids,
        "constructIds": request.construct_ids,
        "contextHash": request.context_hash,
        "sampleVersionId": request.sample_version_id,
        "studyPlanBinding": (
            request.study_plan_binding.model_dump(by_alias=True)
            if request.study_plan_binding is not None
            else None
        ),
        "factorCount": request.factor_count,
        "groupVariableId": request.group_variable_id,
        "aggregationVariableId": request.aggregation_variable_id,
        "outcomeVariableId": request.outcome_variable_id,
        "predictorVariableIds": request.predictor_variable_ids,
        "controlVariableIds": request.control_variable_ids,
        "responseSurfacePredictorIds": request.response_surface_predictor_ids,
        "correlationMethod": request.correlation_method,
        "correlationPAdjust": request.correlation_p_adjust,
        "groupOmnibusPAdjust": request.group_omnibus_p_adjust,
        "multiplicityPAdjust": request.multiplicity_p_adjust,
        "confidenceLevel": request.confidence_level,
        "multiplicityFamilyId": request.multiplicity_family_id,
        "rotation": request.rotation,
        "factorCountMethod": request.factor_count_method,
        "parallelIterations": request.parallel_iterations,
        "randomSeed": request.random_seed,
        "longitudinalPanel": (
            {
                "modelType": request.longitudinal_panel.model_type,
                "measurementMode": request.longitudinal_panel.measurement_mode,
                "subjectVariableId": request.longitudinal_panel.subject_variable_id,
                "waves": [
                    {
                        "label": wave.label,
                        "timeValue": wave.time_value,
                        "xVariableId": wave.x_variable_id,
                        "yVariableId": wave.y_variable_id,
                        "xItemIds": wave.x_item_ids,
                        "yItemIds": wave.y_item_ids,
                    }
                    for wave in request.longitudinal_panel.waves
                ],
                "estimator": request.longitudinal_panel.estimator,
                "missing": request.longitudinal_panel.missing,
                "constrainAcrossTime": request.longitudinal_panel.constrain_across_time,
                "growthShape": request.longitudinal_panel.growth_shape,
                "indicatorScale": request.longitudinal_panel.indicator_scale,
                "invarianceLevel": request.longitudinal_panel.invariance_level,
                "partialInvariancePositions": (
                    request.longitudinal_panel.partial_invariance_positions
                ),
                "cmbSensitivity": request.longitudinal_panel.cmb_sensitivity,
                "compareCompetingModels": (
                    request.longitudinal_panel.compare_competing_models
                ),
                "runRobustnessChecks": request.longitudinal_panel.run_robustness_checks,
                "powerAnalysis": (
                    {
                        "sampleSizes": request.longitudinal_panel.power_analysis.sample_sizes,
                        "replications": request.longitudinal_panel.power_analysis.replications,
                        "targetPower": request.longitudinal_panel.power_analysis.target_power,
                        "alpha": request.longitudinal_panel.power_analysis.alpha,
                        "autoregressiveX": request.longitudinal_panel.power_analysis.autoregressive_x,
                        "autoregressiveY": request.longitudinal_panel.power_analysis.autoregressive_y,
                        "crossLaggedXToY": request.longitudinal_panel.power_analysis.cross_lagged_x_to_y,
                        "crossLaggedYToX": request.longitudinal_panel.power_analysis.cross_lagged_y_to_x,
                        "icc": request.longitudinal_panel.power_analysis.icc,
                        "randomInterceptCorrelation": request.longitudinal_panel.power_analysis.random_intercept_correlation,
                        "withinCorrelation": request.longitudinal_panel.power_analysis.within_correlation,
                        "reliability": request.longitudinal_panel.power_analysis.reliability,
                        "estimateMeasurementError": request.longitudinal_panel.power_analysis.estimate_measurement_error,
                        "seed": request.longitudinal_panel.power_analysis.seed,
                    }
                    if request.longitudinal_panel.power_analysis is not None
                    else None
                ),
            }
            if request.longitudinal_panel is not None
            else None
        ),
        "diaryMultilevel": (
            {
                "analysisType": request.diary_multilevel.analysis_type,
                "subjectVariableId": request.diary_multilevel.subject_variable_id,
                "timeVariableId": request.diary_multilevel.time_variable_id,
                "outcomeVariableId": request.diary_multilevel.outcome_variable_id,
                "predictorVariableId": request.diary_multilevel.predictor_variable_id,
                "mediatorVariableId": request.diary_multilevel.mediator_variable_id,
                "level2CovariateIds": request.diary_multilevel.level2_covariate_ids,
                "controlVariableIds": request.diary_multilevel.control_variable_ids,
                "randomSlope": request.diary_multilevel.random_slope,
                "residualStructure": request.diary_multilevel.residual_structure,
                "outcomeFamily": request.diary_multilevel.outcome_family,
                "countModel": request.diary_multilevel.count_model,
                "zeroProcessPredictors": (
                    request.diary_multilevel.zero_process_predictors
                ),
                "distributionDiagnosticSimulations": (
                    request.diary_multilevel.distribution_diagnostic_simulations
                ),
                "distributionDiagnosticSeed": (
                    request.diary_multilevel.distribution_diagnostic_seed
                ),
                "clusterStructure": request.diary_multilevel.cluster_structure,
                "crossClassVariableId": (
                    request.diary_multilevel.cross_class_variable_id
                ),
                "exposureVariableId": request.diary_multilevel.exposure_variable_id,
                "centering": request.diary_multilevel.centering,
                "mediationType": request.diary_multilevel.mediation_type,
                "temporalEffect": request.diary_multilevel.temporal_effect,
                "lagOrder": request.diary_multilevel.lag_order,
                "expectedTimeInterval": request.diary_multilevel.expected_time_interval,
                "timeIntervalTolerance": request.diary_multilevel.time_interval_tolerance,
                "includeLinearTime": request.diary_multilevel.include_linear_time,
                "includeQuadraticTime": request.diary_multilevel.include_quadratic_time,
                "timeOriginStrategy": request.diary_multilevel.time_origin_strategy,
                "customTimeOrigin": request.diary_multilevel.custom_time_origin,
                "level2ModeratorVariableId": (
                    request.diary_multilevel.level2_moderator_variable_id
                ),
                "expectedObservationsPerPerson": (
                    request.diary_multilevel.expected_observations_per_person
                ),
                "minimumComplianceRate": request.diary_multilevel.minimum_compliance_rate,
                "excludeLowCompliance": request.diary_multilevel.exclude_low_compliance,
                "responseLatencyVariableId": (
                    request.diary_multilevel.response_latency_variable_id
                ),
                "minimumResponseLatency": (
                    request.diary_multilevel.minimum_response_latency
                ),
                "maximumResponseLatency": (
                    request.diary_multilevel.maximum_response_latency
                ),
                "excludeOutOfWindow": request.diary_multilevel.exclude_out_of_window,
                "reliabilityConstructs": [
                    {"label": construct.label, "itemIds": construct.item_ids}
                    for construct in request.diary_multilevel.reliability_constructs
                ],
                "missingStrategy": request.diary_multilevel.missing_strategy,
                "imputationCount": request.diary_multilevel.imputation_count,
                "imputationIterations": request.diary_multilevel.imputation_iterations,
                "runRobustnessChecks": request.diary_multilevel.run_robustness_checks,
                "powerAnalysis": (
                    {
                        "personCounts": request.diary_multilevel.power_analysis.person_counts,
                        "observationsPerPerson": request.diary_multilevel.power_analysis.observations_per_person,
                        "replications": request.diary_multilevel.power_analysis.replications,
                        "targetPower": request.diary_multilevel.power_analysis.target_power,
                        "alpha": request.diary_multilevel.power_analysis.alpha,
                        "withinEffect": request.diary_multilevel.power_analysis.within_effect,
                        "betweenEffect": request.diary_multilevel.power_analysis.between_effect,
                        "randomInterceptSd": request.diary_multilevel.power_analysis.random_intercept_sd,
                        "randomSlopeSd": request.diary_multilevel.power_analysis.random_slope_sd,
                        "residualSd": request.diary_multilevel.power_analysis.residual_sd,
                        "predictorBetweenSd": request.diary_multilevel.power_analysis.predictor_between_sd,
                        "predictorWithinSd": request.diary_multilevel.power_analysis.predictor_within_sd,
                        "residualAr1": request.diary_multilevel.power_analysis.residual_ar1,
                        "seed": request.diary_multilevel.power_analysis.seed,
                    }
                    if request.diary_multilevel.power_analysis is not None
                    else None
                ),
                "dsem": (
                    {
                        "chains": request.diary_multilevel.dsem.chains,
                        "iterations": request.diary_multilevel.dsem.iterations,
                        "warmup": request.diary_multilevel.dsem.warmup,
                        "thin": request.diary_multilevel.dsem.thin,
                        "priorMeanSd": request.diary_multilevel.dsem.prior_mean_sd,
                        "priorScale": request.diary_multilevel.dsem.prior_scale,
                        "randomDynamicSlopes": (
                            request.diary_multilevel.dsem.random_dynamic_slopes
                        ),
                        "plotDrawsPerChain": (
                            request.diary_multilevel.dsem.plot_draws_per_chain
                        ),
                        "predictiveReplications": (
                            request.diary_multilevel.dsem.predictive_replications
                        ),
                        "runPriorSensitivity": (
                            request.diary_multilevel.dsem.run_prior_sensitivity
                        ),
                        "seed": request.diary_multilevel.dsem.seed,
                    }
                    if request.diary_multilevel.dsem is not None
                    else None
                ),
            }
            if request.diary_multilevel is not None
            else None
        ),
    }
