struct VertexIn {
  float3 position : TEXCOORD0;
  float4 color : TEXCOORD1;
};
struct VertexOut {
  float4 position : SV_Position;
  float4 color : TEXCOORD0;
};

cbuffer FrameUniforms : register(b0, space1) {
  float4x4 frame_mvp;
  float4 frame_tint;
};

VertexOut vertex_main(VertexIn input) {
  VertexOut output;
  output.position = mul(frame_mvp, float4(input.position, 1.0));
  output.color = input.color * frame_tint;
  return output;
}

float4 fragment_main(VertexOut input) : SV_Target0 {
  return input.color;
}
