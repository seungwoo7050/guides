# 용어

## attachment

render pass가 읽거나 쓰는 color·depth·stencil image입니다. format, extent, sample count, load/store와 clear 계약을 가집니다.

## barycentric coordinate

삼각형 내부 점을 세 vertex의 weight 합으로 나타내는 좌표입니다. coverage, attribute interpolation과 derivative 계산에 사용합니다.

## clip space

projection 뒤 perspective divide 이전의 homogeneous 공간입니다. 과정에서는 `-w≤x≤w`, `-w≤y≤w`, `0≤z≤w`를 사용합니다.

## command buffer

GPU가 나중에 실행할 copy·render·compute 명령을 기록하는 객체 또는 기록 단위입니다. 기록 완료와 GPU 실행 완료는 다릅니다.

## coverage

primitive가 framebuffer의 특정 sample을 포함하는지의 판정입니다. fragment shader 결과나 alpha와 동일하지 않습니다.

## draw

현재 pipeline, binding과 dynamic state를 사용해 primitive 처리를 요청하는 command입니다. draw 호출이 있었다는 사실만으로 pixel write가 보장되지 않습니다.

## fragment

coverage를 통과한 sample 후보에 대해 보간된 값과 shader 계산을 수행하는 논리 작업입니다. depth·stencil·discard 등으로 attachment write가 없을 수 있습니다.

## frame slot

여러 frame을 동시에 진행할 때 command resource, dynamic upload와 completion token을 묶어 재사용하는 단위입니다.

## handedness

좌표축과 cross product 방향의 convention입니다. camera forward, projection, viewport Y와 winding을 함께 기록해야 합니다.

## linear RGB

조명, filtering과 blending 같은 선형 연산을 수행하는 color 표현입니다. sRGB encoding 값과 구분합니다.

## material

표면 shading에 필요한 parameter와 texture, alpha/culling profile을 묶는 계약입니다. shader code 자체와 동일하지 않습니다.

## mipmap

texture를 low-pass filter하고 단계적으로 축소한 image pyramid입니다. minification footprint에 맞는 주파수 정보를 제공합니다.

## NDC

perspective divide 뒤의 normalized device coordinates입니다. 과정 규약은 x/y `[-1,1]`, z `[0,1]`입니다.

## normal matrix

비균일 scale이 있는 transform에서도 normal과 tangent의 수직 관계를 보존하기 위해 사용하는 model matrix 3×3 부분의 inverse transpose입니다.

## pipeline

shader와 vertex input, topology, rasterization, depth, blend, attachment format 등 draw의 고정 상태를 묶은 GPU 객체입니다.

## premultiplied alpha

RGB가 이미 alpha와 곱해진 표현입니다. filtering과 over compositing의 경계를 단순화하지만 asset과 blend state가 같은 계약을 사용해야 합니다.

## rasterization

projected primitive를 framebuffer sample의 coverage와 fragment 입력으로 바꾸는 단계입니다.

## render pass

attachment와 load/store 계약 안에서 draw를 기록하는 command 범위입니다.

## resource generation

reload·resize·재생성 전후의 같은 logical id를 구분하는 version입니다. stale handle과 in-flight resource retirement에 사용합니다.

## sampler

texture를 읽을 때 filter, address mode, mip/LOD와 anisotropy 같은 방법을 정의하는 상태입니다.

## shader

GPU invocation이 실행하는 program입니다. source, compiler target, stage interface와 resource binding manifest를 함께 관리합니다.

## sRGB

표시·저장을 위한 비선형 RGB encoding입니다. color texture decode와 output encode 경계를 명시해야 합니다.

## swapchain

window에 표시할 image의 획득·render·present lifecycle을 제공하는 체계입니다. acquired image는 일반 장기 asset처럼 보관하지 않습니다.

## texel

texture image의 element입니다. texel center와 normalized coordinate mapping을 sampler convention과 함께 정의합니다.

## top-left rule

shared edge의 경계 sample을 정확히 한 triangle이 소유하도록 일부 edge만 equality를 포함하는 rasterization fill rule입니다.

## uniform

draw 또는 frame에서 shader가 읽는 비교적 작은 parameter data입니다. API에 따라 alignment와 binding 규칙이 다릅니다.

## viewport

NDC를 framebuffer coordinate와 depth range로 mapping하는 상태입니다. 과정은 top-left origin과 `+Y down`을 사용합니다.
