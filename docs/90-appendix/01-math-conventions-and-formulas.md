# 수학 규약과 공식 빠른 참조

## 목적

이 문서는 과정에서 사용하는 그래픽스 수식과 좌표 규약을 한 곳에 모읍니다. 일반 선형대수 설명을 복제하지 않고, 구현·trace·테스트가 같은 convention을 가리키도록 합니다. 수식만 복사하지 말고 입력 공간·유효 범위·실패 조건을 함께 확인합니다.

## 정본 규약

| 항목 | 값 |
|---|---|
| 벡터 | column vector |
| 합성 | `clip = P * V * M * local` |
| world/view | left-handed, camera forward `+Z` |
| NDC | x,y `[-1,1]`, z `[0,1]` |
| viewport | top-left origin, `+Y down` |
| texture | top-left origin, `+V down` |
| sample | pixel center `(x+0.5, y+0.5)` |
| front face | viewport에서 counter-clockwise |
| 색 | 계산은 linear RGB, 표시 출력은 sRGB encode |

## vector

```text
dot(a,b) = ax*bx + ay*by + az*bz
length(v) = sqrt(dot(v,v))
normalize(v) = v / length(v)
```

`length(v)`가 0 또는 매우 작으면 normalize하지 않습니다. epsilon은 입력 단위와 fixture에 맞춰 정하고, invalid 수를 기록합니다.

cross product는 handedness와 operand 순서에 따라 방향이 바뀝니다. basis fixture로 축 방향을 검증합니다.

## transform

position:

```text
p_world = M * vec4(p_local, 1)
```

direction:

```text
d_world = M * vec4(d_local, 0)
```

normal:

```text
Nmat = transpose(inverse(mat3(M)))
n_world = normalize(Nmat * n_local)
```

model matrix가 singular이면 normal matrix가 없습니다. asset/instance를 거부하거나 명시적 fallback 정책을 사용합니다.

## perspective divide와 viewport

```text
p_ndc = p_clip.xyz / p_clip.w
```

`w`가 유한하고 0에서 충분히 떨어진 결과만 divide합니다. clipping은 divide 이전에 수행합니다.

```text
x_screen = vx + (x_ndc * 0.5 + 0.5) * vw
y_screen = vy + (1 - (y_ndc * 0.5 + 0.5)) * vh
z_depth  = z_ndc
```

## clip volume

과정의 homogeneous clip condition:

```text
-w <= x <= w
-w <= y <= w
 0 <= z <= w
```

plane distance의 부호와 inside equality를 구현 전체에서 고정합니다.

## edge function과 barycentric

```text
E(a,b,p) = (px-ax)(by-ay) - (py-ay)(bx-ax)
area = E(v0,v1,v2)
```

weight는 opposite edge의 signed area 비율로 구합니다. 정확한 부호와 vertex 순서는 implementation convention에 따라 fixture로 고정합니다.

```text
lambda0 + lambda1 + lambda2 = 1
```

## perspective-correct attribute

```text
q_i = 1 / w_i
A = (Σ lambda_i * a_i * q_i) / (Σ lambda_i * q_i)
```

flat id는 보간하지 않습니다. normal은 보간 뒤 normalize합니다.

## sRGB transfer

정규화 sRGB 값 `s`를 linear `l`로 decode:

```text
if s <= 0.04045:
    l = s / 12.92
else:
    l = ((s + 0.055) / 1.055) ^ 2.4
```

linear `l`을 sRGB `s`로 encode:

```text
if l <= 0.0031308:
    s = 12.92 * l
else:
    s = 1.055 * l^(1/2.4) - 0.055
```

입력 범위와 clamp 위치를 명시합니다. lighting 중간 값을 자동 clamp하지 않습니다.

## alpha over

straight alpha:

```text
out.rgb = src.rgb * src.a + dst.rgb * (1 - src.a)
out.a   = src.a + dst.a * (1 - src.a)
```

premultiplied alpha:

```text
out.rgb = src.rgb + dst.rgb * (1 - src.a)
out.a   = src.a + dst.a * (1 - src.a)
```

모든 값은 linear color 기준입니다.

## texture coordinate

texel center:

```text
u_i = (i + 0.5) / width
v_j = (j + 0.5) / height
```

bilinear용 연속 texel coordinate의 한 convention:

```text
x = u * width  - 0.5
y = v * height - 0.5
```

address mode를 적용하는 위치와 UV=1의 의미를 fixture로 고정합니다.

## LOD 근사

```text
rho_x = length(vec2(dudx * width, dvdx * height))
rho_y = length(vec2(dudy * width, dvdy * height))
rho   = max(rho_x, rho_y)
lod   = log2(max(rho, tiny))
```

실제 GPU derivative와 정확히 같다고 가정하지 않습니다. 선택 level과 clamp를 기록합니다.

## diffuse 기준선

```text
NdotL = max(dot(N,L), 0)
diffuse = base_color * light_radiance * NdotL / pi
```

world/view 공간, light 단위와 attenuation 정책을 함께 기록합니다.

## frame budget

```text
frame_time_ms = 1000 / FPS
```

FPS가 아니라 ms와 percentile을 비교합니다. CPU와 GPU 시간이 overlap될 수 있으므로 단순 합을 화면 간격으로 단정하지 않습니다.

## 검토표

- 각 vector에 공간과 단위가 있는가?
- matrix 곱 순서와 memory layout을 혼동하지 않았는가?
- clipping 전에 `w`를 버리지 않았는가?
- color 계산이 linear인가?
- texture가 color인지 data인지 구분되는가?
- alpha representation과 blend state가 일치하는가?
- depth convention과 clear/compare가 일치하는가?
- formula 결과의 finite·range 검사가 있는가?
