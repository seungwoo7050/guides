#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
/* [Implementation 1] 원소 독립성과 restrict의 non-alias 계약을 벡터화 가능한 기준으로 둡니다. */
static void saxpy(
    float *restrict output,
    const float *restrict left,
    const float *restrict right,
    float scale,
    size_t count)
{
    size_t index;
    for (index = 0; index < count; ++index)
        output[index] = left[index] * scale + right[index];
}
/* [Implementation 2] 이전 결과를 다음 반복이 소유하는 loop-carried dependency 비교군입니다. */
static float recurrence(const float *input, size_t count)
{
    size_t index;
    float value = 0.0f;
    for (index = 0; index < count; ++index)
        value = value * 0.999f + input[index];
    return value;
}
/* [Implementation 3] 결정적 입력과 관찰 가능한 checksum으로 최적화 뒤 정확성을 고정합니다. */
int main(void)
{
    enum { count = 4096 };
    float *left = malloc(sizeof(*left) * count);
    float *right = malloc(sizeof(*right) * count);
    float *output = malloc(sizeof(*output) * count);
    size_t index;
    double checksum = 0.0;
    float dependent;

    if (left == NULL || right == NULL || output == NULL)
    {
        perror("메모리 할당 실패");
        free(left);
        free(right);
        free(output);
        return 2;
    }
    for (index = 0; index < count; ++index)
    {
        left[index] = (float)index * 0.25f;
        right[index] = (float)(count - index) * 0.5f;
    }
    saxpy(output, left, right, 1.5f, count);
    for (index = 0; index < count; ++index)
        checksum += output[index];
    dependent = recurrence(output, count);

    printf("검사 합계: %.6f, 점화식 결과: %.6f\n", checksum, (double)dependent);
    if (!isfinite(checksum) || !isfinite(dependent)
        || fabs(checksum - 7340288.0) > 0.001
        || fabs((double)dependent - 1624937.25) > 0.001)
    {
        fprintf(stderr, "기준 계산과 다른 결과가 나왔습니다.\n");
        free(left);
        free(right);
        free(output);
        return 1;
    }
    free(left);
    free(right);
    free(output);
    return 0;
}
