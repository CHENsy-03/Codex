# 无人机二维航程计算引擎 协议验收矩阵（TASK-010，含验收补正 R1 与 R1-A）

## 1. 文档目的和范围

本矩阵将冻结设计中的协议要求、测试用例与实际结果建立逐项可追踪关系，作为系统化协议验收记录。
Case ID 是稳定审计标识，**不要求连续，稳定语义优先**；编号空档合法。
本任务不新增业务能力、不修改生产代码；本文件不是发布完成证明。

## 2. 冻结文档名称及 SHA256（3 份逻辑文档；4 个物理文件）

| 逻辑文档 | 物理文件 | 大小 (B) | SHA256 |
| --- | --- | ---: | --- |
| V1.2 业务规则冻结 PRD | 产品文档设计/无人机二维航程计算样品_产品需求文档_V1.2_业务规则冻结.docx | 61292 | `82945F5A2BAF98100ACC4C2BCDC77A803452AAE7DE6AA933A046E459A75265D4` |
| V1.0 Java 21 常驻子进程集成技术设计（冻结版） | 产品文档设计/无人机二维航程计算引擎_Java21常驻子进程集成技术设计_V1.0_冻结版.docx | 155814 | `460C366DEB6071A7A43B1B70C67889154330A68A28D1E4A1CF121814158D229E` |
| V1.2 使用手册（仅一致性检查） | 产品交付文件/无人机二维航程计算平台_产品使用手册_V1.2.docx | 62401 | `F284F34CA96F1DF6D339CE1EAB5A829CBA5D6277D1C6A95516459A29A30E6071` |
| V1.2 使用手册（仅一致性检查） | 产品交付文件/无人机二维航程计算平台_产品使用手册_V1.2.pdf | 816935 | `63F3DC6F4AE19C8E7CF9F6F49C9D98DB11409FD620F02AA9ECA5DB90E31F6504` |

来源优先级：V1.2 冻结 PRD 决定业务规则；V1.0 冻结设计决定 Java 子进程协议、字段和错误码；使用手册只做一致性检查；现有实现不能反过来定义冻结需求。

## 3. 当前代码快照

| 项目 | 值 |
| --- | --- |
| 工作目录 | E:\AI_Projects\Codex\workspace\drone-range-simulation |
| 原仓库分支 | feat/task-016-site-analysis |
| HEAD | 2f4d87a4952884facb8f9a60314b4d850def3d2c |
| 操作系统/时间 | Windows_NT / 2026-08-07（Asia/Shanghai） |
| Python（.venv） | 3.14.7 |
| pytest / rasterio / pyproj | 9.1.1 / 1.5.0 / 3.7.2 |
| 项目文件数 | 41 |

## 4. Case ID 完整矩阵

所有 Case ID 唯一，通过参数化 id 或测试函数名映射到稳定 nodeid；本表 nodeid 由 `pytest --collect-only` 实时采集。
补正后总数 **196**；实际结果全部 **PASS**（无 skip、无 xfail）。

### TRN：传输层：NDJSON/UTF-8/flush/EOF/管道/输出隔离（19 项）

来源：冻结设计 §4 通信通道、§7 传输层要求；TASK-008 冻结行为

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| TRN-001 | `test_TRN_invalid_json[TRN-001]` | PASS |
| TRN-002 | `test_TRN_invalid_json[TRN-002]` | PASS |
| TRN-003 | `test_TRN_invalid_json[TRN-003]` | PASS |
| TRN-004 | `test_TRN_invalid_json[TRN-004]` | PASS |
| TRN-005 | `test_TRN_invalid_json[TRN-005]` | PASS |
| TRN-006 | `test_TRN_invalid_json[TRN-006]` | PASS |
| TRN-007 | `test_TRN_invalid_json[TRN-007]` | PASS |
| TRN-008 | `test_TRN_invalid_json[TRN-008]` | PASS |
| TRN-009 | `test_TRN_invalid_json[TRN-009]` | PASS |
| TRN-010 | `test_TRN_invalid_json[TRN-010]` | PASS |
| TRN-011 | `test_TRN_invalid_json[TRN-011]` | PASS |
| TRN-012 | `test_TRN_invalid_json[TRN-012]` | PASS |
| TRN-013 | `test_TRN_013_subprocess_hello_single_line_flush` | PASS |
| TRN-014 | `test_TRN_014_subprocess_stdin_eof_exit_0_no_extra_output` | PASS |
| TRN-015 | `test_TRN_015_subprocess_stdout_only_protocol_json` | PASS |
| TRN-016 | `test_TRN_016_subprocess_stderr_not_merged_into_stdout` | PASS |
| TRN-017 | `test_TRN_017_subprocess_shutdown_flush_then_exit` | PASS |
| TRN-018 | `test_TRN_018_run_worker_broken_output_pipe_safe_exit` | PASS |
| TRN-019 | `test_TRN_019_subprocess_invalid_then_valid_continues` | PASS |

### ENV：公共请求信封：id/protocolVersion/operation 校验与错误码（11 项）

来源：冻结设计 §5 通用请求字段、§7 错误码

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| ENV-001 | `test_ENV_envelope[ENV-001]` | PASS |
| ENV-002 | `test_ENV_envelope[ENV-002]` | PASS |
| ENV-003 | `test_ENV_envelope[ENV-003]` | PASS |
| ENV-004 | `test_ENV_envelope[ENV-004]` | PASS |
| ENV-005 | `test_ENV_envelope[ENV-005]` | PASS |
| ENV-006 | `test_ENV_envelope[ENV-006]` | PASS |
| ENV-007 | `test_ENV_envelope[ENV-007]` | PASS |
| ENV-008 | `test_ENV_envelope[ENV-008]` | PASS |
| ENV-009 | `test_ENV_envelope[ENV-009]` | PASS |
| ENV-010 | `test_ENV_envelope[ENV-010]` | PASS |
| ENV-011 | `test_ENV_envelope[ENV-011]` | PASS |

### STA：状态机：READY/MAP_LOADED/TERMINATING 与操作许可（13 项）

来源：冻结设计 §3 进程生命周期与状态机

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| STA-001 | `test_STA_001_start_ready` | PASS |
| STA-002 | `test_STA_002_ready_calculate_returns_map_not_loaded_priority` | PASS |
| STA-003 | `test_STA_003_ready_load_success_enters_map_loaded` | PASS |
| STA-004 | `test_STA_004_ready_load_fail_stays_ready` | PASS |
| STA-005 | `test_STA_005_map_loaded_hello_returns_map_loaded` | PASS |
| STA-006 | `test_STA_006_map_loaded_calculate_success_stays_map_loaded` | PASS |
| STA-007 | `test_STA_007_map_loaded_calculate_fail_stays_map_loaded` | PASS |
| STA-008 | `test_STA_008_map_loaded_load_success_switches_map` | PASS |
| STA-009 | `test_STA_009_map_loaded_load_fail_keeps_old_map` | PASS |
| STA-010 | `test_STA_010_unknown_operation_state_unchanged` | PASS |
| STA-011 | `test_STA_011_subprocess_shutdown_terminating_then_exit_0` | PASS |
| STA-012 | `test_STA_012_subprocess_after_shutdown_no_more_processing` | PASS |
| STA-013 | `test_STA_013_no_extra_protocol_states` | PASS |

### MAP：load_map：扩展名、错误映射、元数据、原子替换（001..028 恢复 TASK-010 原语义；029..031 新增非有限仿射；032/033 转换器建立失败）（33 项）

来源：冻结设计 §5 load_map、§10 AC-I02/I03；TASK-010 R1/R1-A 补正

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| MAP-001 | `test_MAP_001_legal_absolute_tif` | PASS |
| MAP-002 | `test_MAP_002_legal_absolute_tiff` | PASS |
| MAP-003 | `test_MAP_003_relative_path_request_invalid` | PASS |
| MAP-004 | `test_MAP_004_path_missing_request_invalid` | PASS |
| MAP-005 | `test_MAP_005_path_non_string_request_invalid` | PASS |
| MAP-006 | `test_MAP_006_path_empty_request_invalid` | PASS |
| MAP-007 | `test_MAP_007_nonexistent_map_not_found` | PASS |
| MAP-008 | `test_MAP_008_directory_map_not_found` | PASS |
| MAP-009 | `test_MAP_009_unreadable_map_not_found` | PASS |
| MAP-010 | `test_MAP_010_corrupt_tiff_open_failed` | PASS |
| MAP-011 | `test_MAP_011_text_fake_tif_open_failed` | PASS |
| MAP-012 | `test_MAP_012_zip_open_failed` | PASS |
| MAP-013 | `test_MAP_013_zip_bytes_as_tif_open_failed` | PASS |
| MAP-014 | `test_MAP_014_geotiff_renamed_non_tiff_ext_open_failed` | PASS |
| MAP-015 | `test_MAP_015_no_crs_crs_missing` | PASS |
| MAP-016 | `test_MAP_016_degenerate_transform_transform_invalid` | PASS |
| MAP-017 | `test_MAP_017_nan_transform_real_validator` | PASS |
| MAP-018 | `test_MAP_018_illegal_band_count_open_failed` | PASS |
| MAP-019 | `test_MAP_019_epsg_crs_string` | PASS |
| MAP-020 | `test_MAP_020_no_epsg_returns_wkt2` | PASS |
| MAP-021 | `test_MAP_021_load_no_preview` | PASS |
| MAP-022 | `test_MAP_022_import_worker_no_qapplication` | PASS |
| MAP-023 | `test_MAP_023_import_worker_no_pyside6` | PASS |
| MAP-024 | `test_MAP_024_success_data_keys_exact` | PASS |
| MAP-025 | `test_MAP_025_atomic_failed_loads_keep_old_map_and_calculation` | PASS |
| MAP-026 | `test_MAP_026_atomic_switch_uses_new_map` | PASS |
| MAP-027 | `test_MAP_027_atomic_multiple_failures_keep_map_loaded` | PASS |
| MAP-028 | `test_MAP_028_switch_release_old_map_no_exception` | PASS |
| MAP-029 | `test_MAP_029_infinity_transform_real_validator` | PASS |
| MAP-030 | `test_MAP_030_minus_infinity_transform_real_validator` | PASS |
| MAP-031 | `test_MAP_031_nonfinite_load_keeps_map_a` | PASS |
| MAP-032 | `test_MAP_032_crs_present_converter_build_failure_ready` | PASS |
| MAP-033 | `test_MAP_033_crs_present_converter_build_failure_atomic` | PASS |

### PNT：三类坐标：wgs84/map_crs/pixel 数值规则与范围（50 项）

来源：冻结设计 §5 三类坐标、§10 AC-I04/I05

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| PNT-001 | `test_PNT_combos[PNT-001]` | PASS |
| PNT-002 | `test_PNT_combos[PNT-002]` | PASS |
| PNT-003 | `test_PNT_combos[PNT-003]` | PASS |
| PNT-004 | `test_PNT_combos[PNT-004]` | PASS |
| PNT-005 | `test_PNT_combos[PNT-005]` | PASS |
| PNT-006 | `test_PNT_combos[PNT-006]` | PASS |
| PNT-007 | `test_PNT_combos[PNT-007]` | PASS |
| PNT-008 | `test_PNT_combos[PNT-008]` | PASS |
| PNT-009 | `test_PNT_combos[PNT-009]` | PASS |
| PNT-010 | `test_PNT_integer_and_float_pixel[PNT-010]` | PASS |
| PNT-011 | `test_PNT_integer_and_float_pixel[PNT-011]` | PASS |
| PNT-012 | `test_PNT_invalid_coordinate_values[PNT-012]` | PASS |
| PNT-013 | `test_PNT_invalid_coordinate_values[PNT-013]` | PASS |
| PNT-014 | `test_PNT_invalid_coordinate_values[PNT-014]` | PASS |
| PNT-015 | `test_PNT_invalid_coordinate_values[PNT-015]` | PASS |
| PNT-016 | `test_PNT_invalid_coordinate_values[PNT-016]` | PASS |
| PNT-017 | `test_PNT_017_nonfinite_coordinate_rejected` | PASS |
| PNT-018 | `test_PNT_018_full_precision_no_truncation` | PASS |
| PNT-019 | `test_PNT_019_decimal_pixel_not_rounded` | PASS |
| PNT-020 | `test_PNT_020_no_automatic_0p5` | PASS |
| PNT-021 | `test_PNT_021_wgs84_lon_minus_180_valid` | PASS |
| PNT-022 | `test_PNT_022_wgs84_lon_180_range_valid_but_out_of_bounds` | PASS |
| PNT-023 | `test_PNT_023_wgs84_lat_minus_90_out_of_bounds` | PASS |
| PNT-024 | `test_PNT_024_wgs84_lat_90_valid` | PASS |
| PNT-025 | `test_PNT_025_wgs84_just_out_of_range_invalid` | PASS |
| PNT-026 | `test_PNT_026_wgs84_missing_field_invalid` | PASS |
| PNT-027 | `test_PNT_027_wgs84_always_xy_not_swapped` | PASS |
| PNT-028 | `test_PNT_028_wgs84_in_image_success` | PASS |
| PNT-029 | `test_PNT_029_wgs84_out_of_image_out_of_bounds` | PASS |
| PNT-030 | `test_PNT_030_map_crs_x_y_fields` | PASS |
| PNT-031 | `test_PNT_031_map_crs_no_x_y_swap` | PASS |
| PNT-032 | `test_PNT_032_map_crs_full_inverse_affine` | PASS |
| PNT-033 | `test_PNT_033_map_crs_in_bounds_success` | PASS |
| PNT-034 | `test_PNT_034_map_crs_out_of_bounds` | PASS |
| PNT-035 | `test_PNT_035_map_crs_transform_failure_crs_transform` | PASS |
| PNT-036 | `test_PNT_036_pixel_origin_ok` | PASS |
| PNT-037 | `test_PNT_037_pixel_near_edge_valid_decimal` | PASS |
| PNT-038 | `test_PNT_038_pixel_column_width_out_of_bounds` | PASS |
| PNT-039 | `test_PNT_039_pixel_row_height_out_of_bounds` | PASS |
| PNT-040 | `test_PNT_040_pixel_negative_out_of_bounds` | PASS |
| PNT-041 | `test_PNT_041_pixel_decimal_coordinates` | PASS |
| PNT-042 | `test_PNT_042_pixel_no_column_row_swap` | PASS |
| PNT-043 | `test_PNT_043_pixel_no_0p5` | PASS |
| PNT-044 | `test_PNT_044_rotated_transform_calculate` | PASS |
| PNT-045 | `test_PNT_error_codes[PNT-045]` | PASS |
| PNT-046 | `test_PNT_error_codes[PNT-046]` | PASS |
| PNT-047 | `test_PNT_error_codes[PNT-047]` | PASS |
| PNT-048 | `test_PNT_error_codes[PNT-048]` | PASS |
| PNT-049 | `test_PNT_049_out_of_bounds_via_protocol` | PASS |
| PNT-050 | `test_PNT_050_crs_transform_via_protocol` | PASS |

### CAL：calculate：速度/距离/时间/响应结构与边界（025 为既有合并时间公式用例；024/026/027 为新增）（35 项）

来源：V1.2 PRD 附录 B 关键参数冻结清单；冻结设计 §6 计算

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| CAL-001 | `test_CAL_001_speed_1_success` | PASS |
| CAL-002 | `test_CAL_002_speed_99_success` | PASS |
| CAL-003 | `test_CAL_003_speed_missing_request_invalid` | PASS |
| CAL-004 | `test_CAL_speed_invalid[CAL-004]` | PASS |
| CAL-005 | `test_CAL_speed_invalid[CAL-005]` | PASS |
| CAL-006 | `test_CAL_speed_invalid[CAL-006]` | PASS |
| CAL-007 | `test_CAL_speed_invalid[CAL-007]` | PASS |
| CAL-008 | `test_CAL_speed_invalid[CAL-008]` | PASS |
| CAL-009 | `test_CAL_speed_invalid[CAL-009]` | PASS |
| CAL-010 | `test_CAL_speed_invalid[CAL-010]` | PASS |
| CAL-011 | `test_CAL_speed_invalid[CAL-011]` | PASS |
| CAL-012 | `test_CAL_speed_invalid[CAL-012]` | PASS |
| CAL-013 | `test_CAL_speed_invalid[CAL-013]` | PASS |
| CAL-014 | `test_CAL_speed_invalid[CAL-014]` | PASS |
| CAL-015 | `test_CAL_015_same_point_zero` | PASS |
| CAL-016 | `test_CAL_016_short_distance` | PASS |
| CAL-017 | `test_CAL_017_normal_distance` | PASS |
| CAL-018 | `test_CAL_018_high_precision_decimals` | PASS |
| CAL-019 | `test_CAL_019_three_types_same_physical_points` | PASS |
| CAL-020 | `test_CAL_020_epsg4326_map` | PASS |
| CAL-021 | `test_CAL_021_epsg3857_map` | PASS |
| CAL-022 | `test_CAL_022_other_projected_crs` | PASS |
| CAL-023 | `test_CAL_023_rotated_shear_transform` | PASS |
| CAL-024 | `test_CAL_024_independent_geod_diff_within_0p5` | PASS |
| CAL-025 | `test_CAL_025_time_formulas` | PASS |
| CAL-026 | `test_CAL_026_rounded_seconds_formula` | PASS |
| CAL-027 | `test_CAL_027_duration_divmod` | PASS |
| CAL-028 | `test_CAL_028_359999_seconds_success` | PASS |
| CAL-029 | `test_CAL_029_360000_seconds_time_limit` | PASS |
| CAL-030 | `test_CAL_030_greater_360000_time_limit` | PASS |
| CAL-031 | `test_CAL_031_time_limit_no_partial_data` | PASS |
| CAL-032 | `test_CAL_032_calculate_failure_keeps_map` | PASS |
| CAL-033 | `test_CAL_033_simulated_calculation_failure` | PASS |
| CAL-034 | `test_CAL_034_success_data_keys_exact` | PASS |
| CAL-035 | `test_CAL_035_point_keys_exact` | PASS |

### ERR：17 个冻结错误码经公共协议入口触发（18 项）

来源：冻结设计 §7 错误码；V1.2 PRD 异常口径

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| ERR-001 | `test_ERR_001_protocol_invalid_json` | PASS |
| ERR-002 | `test_ERR_002_protocol_version` | PASS |
| ERR-003 | `test_ERR_003_operation_unknown` | PASS |
| ERR-004 | `test_ERR_004_request_invalid` | PASS |
| ERR-005 | `test_ERR_005_internal_last_resort` | PASS |
| ERR-006 | `test_ERR_006_map_not_loaded` | PASS |
| ERR-007 | `test_ERR_007_map_not_found` | PASS |
| ERR-008 | `test_ERR_008_map_open_failed` | PASS |
| ERR-009 | `test_ERR_009_map_crs_missing` | PASS |
| ERR-010 | `test_ERR_010_map_transform_invalid` | PASS |
| ERR-011 | `test_ERR_011_point_type` | PASS |
| ERR-012 | `test_ERR_012_point_invalid` | PASS |
| ERR-013 | `test_ERR_013_point_out_of_bounds` | PASS |
| ERR-014 | `test_ERR_014_crs_transform` | PASS |
| ERR-015 | `test_ERR_015_speed_invalid` | PASS |
| ERR-016 | `test_ERR_016_time_limit` | PASS |
| ERR-017 | `test_ERR_017_calculation` | PASS |
| ERR-018 | `test_ERR_018_message_purity` | PASS |

### LIF：常驻进程生命周期与真实子进程验收（既有稳定 ID：001/005/006/011，允许空档）（4 项）

来源：冻结设计 §3 生命周期、§10 AC-I10/I14

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| LIF-001 | `test_LIF_001_subprocess_full_sequence` | PASS |
| LIF-005 | `test_LIF_005_subprocess_business_error_then_success` | PASS |
| LIF-006 | `test_LIF_006_subprocess_switch_map_result_matches_baseline` | PASS |
| LIF-011 | `test_LIF_011_subprocess_state_continuity_after_100_calculates` | PASS |

### V12：V1.2 业务规则独立交叉基准（13 项）

来源：V1.2 PRD 附录 B；TASK-010 独立 oracle 方法

| Case ID | pytest nodeid | 实际结果 |
| --- | --- | --- |
| V12-001 | `test_V12_001_same_point_zero` | PASS |
| V12-002 | `test_V12_002_short_distance` | PASS |
| V12-003 | `test_V12_003_high_precision_wgs84` | PASS |
| V12-004 | `test_V12_004_pixel_input` | PASS |
| V12-005 | `test_V12_005_map_crs_input` | PASS |
| V12-006 | `test_V12_006_three_types_same_physical_point` | PASS |
| V12-007 | `test_V12_007_rotated_shear_affine` | PASS |
| V12-008 | `test_V12_008_speed_1` | PASS |
| V12-009 | `test_V12_009_speed_99` | PASS |
| V12-010 | `test_V12_010_359999_success_boundary` | PASS |
| V12-011 | `test_V12_011_360000_failure_boundary` | PASS |
| V12-012 | `test_V12_012_real_far_distance_time_limit` | PASS |
| V12-013 | `test_V12_013_no_ui_precision_truncation` | PASS |

## 5. 17 个冻结错误码总表

| 错误码 | 触发验证 nodeid | 结果 |
| --- | --- | --- |
| E_PROTOCOL_INVALID_JSON | `tests/test_protocol_acceptance_matrix.py::test_ERR_001_protocol_invalid_json` | PASS |
| E_PROTOCOL_VERSION | `tests/test_protocol_acceptance_matrix.py::test_ENV_envelope[ENV-002]` | PASS |
| E_OPERATION_UNKNOWN | `tests/test_protocol_acceptance_matrix.py::test_ENV_envelope[ENV-011]` | PASS |
| E_REQUEST_INVALID | `tests/test_protocol_acceptance_matrix.py::test_ERR_004_request_invalid` | PASS |
| E_INTERNAL | `tests/test_protocol_acceptance_matrix.py::test_ERR_005_internal_last_resort` | PASS |
| E_MAP_NOT_LOADED | `tests/test_protocol_acceptance_matrix.py::test_ERR_006_map_not_loaded` | PASS |
| E_MAP_NOT_FOUND | `tests/test_protocol_acceptance_matrix.py::test_ERR_007_map_not_found` | PASS |
| E_MAP_OPEN_FAILED | `tests/test_protocol_acceptance_matrix.py::test_ERR_008_map_open_failed` | PASS |
| E_MAP_CRS_MISSING | `tests/test_protocol_acceptance_matrix.py::test_MAP_032_crs_present_converter_build_failure_ready` | PASS |
| E_MAP_TRANSFORM_INVALID | `tests/test_protocol_acceptance_matrix.py::test_MAP_017_nan_transform_real_validator` | PASS |
| E_POINT_TYPE | `tests/test_protocol_acceptance_matrix.py::test_ERR_011_point_type` | PASS |
| E_POINT_INVALID | `tests/test_protocol_acceptance_matrix.py::test_ERR_012_point_invalid` | PASS |
| E_POINT_OUT_OF_BOUNDS | `tests/test_protocol_acceptance_matrix.py::test_ERR_013_point_out_of_bounds` | PASS |
| E_CRS_TRANSFORM | `tests/test_protocol_acceptance_matrix.py::test_ERR_014_crs_transform` | PASS |
| E_SPEED_INVALID | `tests/test_protocol_acceptance_matrix.py::test_ERR_015_speed_invalid` | PASS |
| E_TIME_LIMIT | `tests/test_protocol_acceptance_matrix.py::test_ERR_016_time_limit` | PASS |
| E_CALCULATION | `tests/test_protocol_acceptance_matrix.py::test_ERR_017_calculation` | PASS |

## 6. 状态转换总表

| 前置状态 | 操作 | 结果状态 | 验证 |
| --- | --- | --- | --- |
| READY | hello | READY | STA-001 |
| READY | calculate | READY + E_MAP_NOT_LOADED | STA-002 |
| READY | load_map 成功 | MAP_LOADED | STA-003 |
| READY | load_map 失败 | READY | STA-004 |
| MAP_LOADED | hello | MAP_LOADED | STA-005 |
| MAP_LOADED | calculate 成功 | MAP_LOADED | STA-006 |
| MAP_LOADED | calculate 失败 | MAP_LOADED | STA-007 |
| MAP_LOADED | load_map 成功 | MAP_LOADED（切换新地图） | STA-008 / MAP-026 / LIF-006 |
| MAP_LOADED | load_map 失败 | MAP_LOADED（保留旧地图） | STA-009 / MAP-025 |
| READY/MAP_LOADED | 未知操作 | 状态不变 + E_OPERATION_UNKNOWN | STA-010 |
| READY/MAP_LOADED | shutdown | TERMINATING → 退出 | STA-011 / TRN-017 |
| TERMINATING | 任何输入 | 不再处理 | STA-012 |

不存在的协议状态：ERROR、LOADING、CALCULATING（STA-013 验证）。

## 7. 响应字段总表

成功响应顶层仅 `id/success/data`；失败响应顶层仅 `id/success/error`；error 仅 `code/message`。
逐项键集合断言见：CAL-034/CAL-035、ERR-001..018、assert_success_shape/assert_error_shape。

## 8. stdout/stderr 审计

- 静态审计（rg 扫描 worker 路径）：PySide6/QApplication/QMainWindow/preview/zipfile/http/gRPC/WebSocket/sqlite/asyncio/ThreadPool/multiprocess/round(/traceback/shell=True/subprocess 均 0 代码命中（QApplication 仅出现在文档字符串）；current_map 仅为实例属性；错误分类全部基于稳定异常类型，无 message 字符串匹配。
- 动态测试：TRN-013..019、ERR-018、LIF-001 等验证 flush、EOF、管道断开、stdout 纯净性与 stderr 隔离。

## 9. 未定义且未冻结的行为（不新增协议承诺）

- 重复 JSON key 的处理顺序；
- 超大请求行限制；
- 多错误请求的未冻结错误优先级；
- JSON 对象键顺序；
- 未冻结的扩展字段；
- 未冻结的并发语义（本阶段为严格串行）。

## 10. TASK-009 文件账目勘误

TASK-009 回执第 14 节文字误将 app/headless_core.py、app/worker_protocol.py 列入“28 个未修改文件”。经重新核验，正确账目为：修改前 34 项；修改 6 项；新增 2 项；未修改 28 项；完成后 36 项；用户文档哈希未变。仅涉及回执文字。

## 11. TASK-010 验收补正 R1 记录

1. Case ID 数量：PNT 46→50、CAL 32→35、MAP 28→33、LIF 4；总计 196。
2. CRS 存在但转换器建立失败：MAP-032（READY）、MAP-033（MAP_LOADED 原子保留），返回 E_MAP_CRS_MISSING。
3. 非有限仿射经真实生产校验器：真实写入 NaN/±Infinity 仿射（MAP-017/029/030/031，R1 阶段编号），移除弱测试。
4. 文档哈希统一为 3 份逻辑文档 / 4 个物理文件。
5. V1.2 最大误差表述纠正：可比较距离用例 11 项，最大绝对误差 0 m。

## 12. TASK-010 验收补正 R1-A：Case ID 稳定性修复

Case ID 是稳定审计标识，不要求连续，稳定语义优先。R1 阶段对 MAP-018..020、LIF 的重编号改变了既有 ID 含义，R1-A 予以恢复：

### MAP 旧 ID → 最终 ID → 语义

| 旧 ID（R1 阶段） | 最终 ID | 语义 | 说明 |
| --- | --- | --- | --- |
| MAP-018（+Infinity） | MAP-029 | +Infinity 仿射 → E_MAP_TRANSFORM_INVALID | 新增 |
| MAP-019（−Infinity） | MAP-030 | −Infinity 仿射 → E_MAP_TRANSFORM_INVALID | 新增 |
| MAP-020（非有限原子保留） | MAP-031 | 已加载 A 时非有限 B 失败且原子保留 A | 新增 |
| MAP-021（非法波段） | MAP-018 | 非法波段 → E_MAP_OPEN_FAILED | 恢复原语义 |
| MAP-022（EPSG CRS） | MAP-019 | EPSG CRS 输出 | 恢复原语义 |
| MAP-023（WKT2） | MAP-020 | 无 EPSG 返回规范化 WKT2 | 恢复原语义 |
| MAP-024（无 preview） | MAP-021 | 不生成 preview | 恢复原语义 |
| MAP-025（无 QApplication） | MAP-022 | 不创建 QApplication | 恢复原语义 |
| MAP-026（无 PySide6） | MAP-023 | 导入链无 PySide6 | 恢复原语义 |
| MAP-027（data 键集合） | MAP-024 | 成功 data 键集合精确 | 恢复原语义 |
| MAP-028（原子失败保留） | MAP-025 | 失败加载保留旧地图与结果 | 恢复原语义 |
| MAP-029（原子切换） | MAP-026 | 成功切换使用新地图 | 恢复原语义 |
| MAP-030（多次失败保持） | MAP-027 | 多次失败不降级 | 恢复原语义 |
| MAP-031（释放无异常） | MAP-028 | 替换/释放旧地图无异常 | 恢复原语义 |
| MAP-032 | MAP-032 | CRS 存在但转换器建立失败，READY 保持 | 保持不变 |
| MAP-033 | MAP-033 | CRS 存在但转换器建立失败，MAP_LOADED 原子保留 | 保持不变 |

MAP-017 保持“非有限仿射参数”语义（现以真实 NaN GeoTIFF 验证）。

### CAL 旧 ID → 最终 ID → 语义

| R1 前 Case ID | R1 后最终 ID | 测试语义 | 是否既有 | 是否新增/拆分 | 既有 ID 含义是否变化 |
| --- | --- | --- | --- | --- | --- |
| CAL-001..023 | CAL-001..023 | 速度/距离/时间/响应既有用例 | 是 | 否 | 否 |
| CAL-024（空缺） | CAL-024 | 独立 Geod 基准差异 ≤0.5 m | 否 | 新增 | 不适用 |
| CAL-025（合并时间公式） | CAL-025 | exact/rounded/duration 三个时间公式（合并） | 是 | 否（恢复原合并语义） | 否 |
| CAL-026（空缺） | CAL-026 | roundedSeconds=ceil(exactSeconds)（拆分自 CAL-025） | 否 | 拆分新增 | 不适用 |
| CAL-027（空缺） | CAL-027 | duration 由同一 roundedSeconds 经 divmod 生成（拆分自 CAL-025） | 否 | 拆分新增 | 不适用 |
| CAL-028..035 | CAL-028..035 | 边界与响应既有用例 | 是 | 否 | 否 |

### LIF 最终 ID 集合

恢复既有稳定 ID：**LIF-001、LIF-005、LIF-006、LIF-011**（编号存在空档合法，不要求连续）。

## 13. 声明

本矩阵是协议验收与追踪记录，**不是发布完成证明**；Java 示例、Nuitka 构建、交付包均未完成。
