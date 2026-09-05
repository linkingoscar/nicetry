import type {
  EmpiricalAnalysisJob,
  EmpiricalAnalysisOptions,
  EmpiricalAnalysisSegmentMap,
} from '../types'
import type { EmpiricalAnalysisRequest } from './contracts'
import { requestJson } from './client'

const empiricalBase = (datasetId: string, measurementVersion: number | null) =>
  `/api/v1/datasets/${datasetId}${measurementVersion === null ? '' : `/measurements/${measurementVersion}`}`

export function runEmpiricalAnalysis(
  datasetId: string,
  measurementVersion: number | null,
  options: EmpiricalAnalysisOptions,
): Promise<EmpiricalAnalysisJob> {
  const body = {
    procedure: options.procedure ?? null,
    analysis_variable_ids: options.analysisVariableIds ?? [],
    construct_ids: options.constructIds ?? [],
    context_hash: options.contextHash ?? null,
    factor_count: options.factorCount,
    sample_version_id: options.sampleVersionId ?? null,
    study_plan_binding: options.studyPlanBinding,
    group_variable_id: options.groupVariableId,
    aggregation_variable_id: options.aggregationVariableId,
    outcome_variable_id: options.outcomeVariableId,
    predictor_variable_ids: options.predictorVariableIds,
    control_variable_ids: options.controlVariableIds,
    response_surface_predictor_ids: options.responseSurfacePredictorIds ?? [],
    correlation_method: options.correlationMethod ?? 'pearson',
    correlation_p_adjust: options.correlationPAdjust ?? 'BH',
    group_omnibus_p_adjust: options.groupOmnibusPAdjust ?? 'holm',
    multiplicity_p_adjust: options.multiplicityPAdjust ?? 'BH',
    confidence_level: options.confidenceLevel ?? 0.95,
    multiplicity_family_id: options.multiplicityFamilyId ?? 'cross_sectional_inference',
    rotation: options.rotation ?? 'varimax',
    factor_count_method: options.factorCountMethod ?? 'kaiser',
    parallel_iterations: options.parallelIterations ?? 1000,
    random_seed: options.randomSeed ?? 20260714,
    longitudinal_panel: options.longitudinalPanel ? {
      model_type: options.longitudinalPanel.modelType,
      measurement_mode: options.longitudinalPanel.measurementMode,
      subject_variable_id: options.longitudinalPanel.subjectVariableId,
      waves: options.longitudinalPanel.waves.map((wave) => ({
        label: wave.label,
        time_value: wave.timeValue,
        x_variable_id: wave.xVariableId,
        y_variable_id: wave.yVariableId,
        x_item_ids: wave.xItemIds,
        y_item_ids: wave.yItemIds,
      })),
      estimator: options.longitudinalPanel.estimator,
      missing: options.longitudinalPanel.missing,
      constrain_across_time: options.longitudinalPanel.constrainAcrossTime,
      growth_shape: options.longitudinalPanel.growthShape,
      indicator_scale: options.longitudinalPanel.indicatorScale,
      invariance_level: options.longitudinalPanel.invarianceLevel,
      partial_invariance_positions: options.longitudinalPanel.partialInvariancePositions,
      cmb_sensitivity: options.longitudinalPanel.cmbSensitivity,
      compare_competing_models: options.longitudinalPanel.compareCompetingModels,
      run_robustness_checks: options.longitudinalPanel.runRobustnessChecks,
      power_analysis: options.longitudinalPanel.powerAnalysis ? {
        sample_sizes: options.longitudinalPanel.powerAnalysis.sampleSizes,
        replications: options.longitudinalPanel.powerAnalysis.replications,
        target_power: options.longitudinalPanel.powerAnalysis.targetPower,
        alpha: options.longitudinalPanel.powerAnalysis.alpha,
        autoregressive_x: options.longitudinalPanel.powerAnalysis.autoregressiveX,
        autoregressive_y: options.longitudinalPanel.powerAnalysis.autoregressiveY,
        cross_lagged_x_to_y: options.longitudinalPanel.powerAnalysis.crossLaggedXToY,
        cross_lagged_y_to_x: options.longitudinalPanel.powerAnalysis.crossLaggedYToX,
        icc: options.longitudinalPanel.powerAnalysis.icc,
        random_intercept_correlation:
          options.longitudinalPanel.powerAnalysis.randomInterceptCorrelation,
        within_correlation: options.longitudinalPanel.powerAnalysis.withinCorrelation,
        reliability: options.longitudinalPanel.powerAnalysis.reliability,
        estimate_measurement_error:
          options.longitudinalPanel.powerAnalysis.estimateMeasurementError,
        seed: options.longitudinalPanel.powerAnalysis.seed,
      } : null,
    } : null,
    diary_multilevel: options.diaryMultilevel ? {
      analysis_type: options.diaryMultilevel.analysisType,
      subject_variable_id: options.diaryMultilevel.subjectVariableId,
      time_variable_id: options.diaryMultilevel.timeVariableId,
      outcome_variable_id: options.diaryMultilevel.outcomeVariableId,
      predictor_variable_id: options.diaryMultilevel.predictorVariableId,
      mediator_variable_id: options.diaryMultilevel.mediatorVariableId,
      level2_covariate_ids: options.diaryMultilevel.level2CovariateIds,
      control_variable_ids: options.diaryMultilevel.controlVariableIds,
      random_slope: options.diaryMultilevel.randomSlope,
      residual_structure: options.diaryMultilevel.residualStructure,
      outcome_family: options.diaryMultilevel.outcomeFamily,
      count_model: options.diaryMultilevel.countModel,
      zero_process_predictors: options.diaryMultilevel.zeroProcessPredictors,
      distribution_diagnostic_simulations:
        options.diaryMultilevel.distributionDiagnosticSimulations,
      distribution_diagnostic_seed:
        options.diaryMultilevel.distributionDiagnosticSeed,
      cluster_structure: options.diaryMultilevel.clusterStructure,
      cross_class_variable_id: options.diaryMultilevel.crossClassVariableId,
      exposure_variable_id: options.diaryMultilevel.exposureVariableId,
      centering: options.diaryMultilevel.centering,
      mediation_type: options.diaryMultilevel.mediationType,
      temporal_effect: options.diaryMultilevel.temporalEffect,
      lag_order: options.diaryMultilevel.lagOrder,
      expected_time_interval: options.diaryMultilevel.expectedTimeInterval,
      time_interval_tolerance: options.diaryMultilevel.timeIntervalTolerance,
      include_linear_time: options.diaryMultilevel.includeLinearTime,
      include_quadratic_time: options.diaryMultilevel.includeQuadraticTime,
      time_origin_strategy: options.diaryMultilevel.timeOriginStrategy,
      custom_time_origin: options.diaryMultilevel.customTimeOrigin,
      level2_moderator_variable_id: options.diaryMultilevel.level2ModeratorVariableId,
      expected_observations_per_person: options.diaryMultilevel.expectedObservationsPerPerson,
      minimum_compliance_rate: options.diaryMultilevel.minimumComplianceRate,
      exclude_low_compliance: options.diaryMultilevel.excludeLowCompliance,
      response_latency_variable_id: options.diaryMultilevel.responseLatencyVariableId,
      minimum_response_latency: options.diaryMultilevel.minimumResponseLatency,
      maximum_response_latency: options.diaryMultilevel.maximumResponseLatency,
      exclude_out_of_window: options.diaryMultilevel.excludeOutOfWindow,
      reliability_constructs: options.diaryMultilevel.reliabilityConstructs.map(
        (construct) => ({ label: construct.label, item_ids: construct.itemIds }),
      ),
      missing_strategy: options.diaryMultilevel.missingStrategy,
      imputation_count: options.diaryMultilevel.imputationCount,
      imputation_iterations: options.diaryMultilevel.imputationIterations,
      run_robustness_checks: options.diaryMultilevel.runRobustnessChecks,
      power_analysis: options.diaryMultilevel.powerAnalysis ? {
        person_counts: options.diaryMultilevel.powerAnalysis.personCounts,
        observations_per_person:
          options.diaryMultilevel.powerAnalysis.observationsPerPerson,
        replications: options.diaryMultilevel.powerAnalysis.replications,
        target_power: options.diaryMultilevel.powerAnalysis.targetPower,
        alpha: options.diaryMultilevel.powerAnalysis.alpha,
        within_effect: options.diaryMultilevel.powerAnalysis.withinEffect,
        between_effect: options.diaryMultilevel.powerAnalysis.betweenEffect,
        random_intercept_sd: options.diaryMultilevel.powerAnalysis.randomInterceptSd,
        random_slope_sd: options.diaryMultilevel.powerAnalysis.randomSlopeSd,
        residual_sd: options.diaryMultilevel.powerAnalysis.residualSd,
        predictor_between_sd: options.diaryMultilevel.powerAnalysis.predictorBetweenSd,
        predictor_within_sd: options.diaryMultilevel.powerAnalysis.predictorWithinSd,
        residual_ar1: options.diaryMultilevel.powerAnalysis.residualAr1,
        seed: options.diaryMultilevel.powerAnalysis.seed,
      } : null,
      dsem: options.diaryMultilevel.dsem ? {
        chains: options.diaryMultilevel.dsem.chains,
        iterations: options.diaryMultilevel.dsem.iterations,
        warmup: options.diaryMultilevel.dsem.warmup,
        thin: options.diaryMultilevel.dsem.thin,
        prior_mean_sd: options.diaryMultilevel.dsem.priorMeanSd,
        prior_scale: options.diaryMultilevel.dsem.priorScale,
        random_dynamic_slopes: options.diaryMultilevel.dsem.randomDynamicSlopes,
        plot_draws_per_chain: options.diaryMultilevel.dsem.plotDrawsPerChain,
        predictive_replications: options.diaryMultilevel.dsem.predictiveReplications,
        run_prior_sensitivity: options.diaryMultilevel.dsem.runPriorSensitivity,
        seed: options.diaryMultilevel.dsem.seed,
      } : null,
    } : null,
  } satisfies EmpiricalAnalysisRequest
  return requestJson<EmpiricalAnalysisJob>(
    `${empiricalBase(datasetId, measurementVersion)}/empirical-analysis`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
}

export function getEmpiricalAnalysisJob(runId: string, signal?: AbortSignal): Promise<EmpiricalAnalysisJob> {
  return requestJson<EmpiricalAnalysisJob>(`/api/v1/analyses/${runId}`, { signal })
}

export function cancelEmpiricalAnalysisJob(runId: string): Promise<EmpiricalAnalysisJob> {
  return requestJson<EmpiricalAnalysisJob>(`/api/v1/analyses/${runId}`, {
    method: 'DELETE',
  })
}

export function empiricalAnalysisExportUrl(
  datasetId: string,
  measurementVersion: number | null,
  reportId: string,
): string {
  return `${empiricalBase(datasetId, measurementVersion)}/empirical-analyses/${reportId}/export`
}

export function getEmpiricalSegment<Segment extends keyof EmpiricalAnalysisSegmentMap>(
  datasetId: string,
  measurementVersion: number | null,
  reportId: string,
  segment: Segment,
): Promise<EmpiricalAnalysisSegmentMap[Segment]> {
  return requestJson<EmpiricalAnalysisSegmentMap[Segment]>(
    `${empiricalBase(datasetId, measurementVersion)}/empirical-analyses/${reportId}/segments/${segment}`,
  )
}
