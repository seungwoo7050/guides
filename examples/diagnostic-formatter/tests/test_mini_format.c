#include "mini_format.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

#define EXPECT(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "실패 %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

int main(void)
{
    char buffer[64];
    char small[5];
    char binary[8];
    int length;

    length = mini_snprintf(buffer, sizeof buffer, "%s:%d:%c:%%", "value", -42, 'X');
    EXPECT(length == (int)strlen("value:-42:X:%"));
    EXPECT(strcmp(buffer, "value:-42:X:%") == 0);

    length = mini_snprintf(buffer, sizeof buffer, "%d", INT_MIN);
    EXPECT(length == snprintf(NULL, 0, "%d", INT_MIN));
    EXPECT(strcmp(buffer, "-2147483648") == 0 || sizeof(int) != 4);

    length = mini_snprintf(small, sizeof small, "abcdef");
    EXPECT(length == 6);
    EXPECT(strcmp(small, "abcd") == 0);

    length = mini_snprintf(NULL, 0, "hello %s", "world");
    EXPECT(length == 11);

    length = mini_snprintf(binary, sizeof binary, "A%cB", 0);
    EXPECT(length == 3);
    EXPECT(binary[0] == 'A' && binary[1] == '\0' && binary[2] == 'B' && binary[3] == '\0');

    EXPECT(mini_snprintf(buffer, sizeof buffer, "bad %") == -1);
    EXPECT(buffer[0] == '\0');
    EXPECT(mini_snprintf(buffer, sizeof buffer, "%x", 1) == -1);
    EXPECT(mini_snprintf(buffer, sizeof buffer, "%s", (const char *)NULL) == 6);
    EXPECT(strcmp(buffer, "(null)") == 0);

    puts("diagnostic-formatter 검사: 통과");
    return 0;
}
