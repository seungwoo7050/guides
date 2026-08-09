# Known-bad mutation registry

검사기는 다음 ID를 public contract에 연결합니다: `swap_matrix_order`, `skip_clipping`, `break_top_left_rule`, `use_affine_uv`, `skip_srgb_decode`, `reverse_depth_convention`, `mismatch_alpha_blend`, `mismatch_vertex_layout`, `overwrite_frame_slot`, `use_stale_resize_attachment`.

mutation은 정답 갱신용 옵션이 아닙니다. 임시 build에서 하나씩 활성화하고, 해당 stage의 독립 oracle이 지정된 이유로 거부하는지 확인합니다.
