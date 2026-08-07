#ifndef TEXTKIT_H
#define TEXTKIT_H

#include <stddef.h>

size_t textkit_length(const char *text);
size_t textkit_count_char(const char *text, char needle);
size_t textkit_word_count(const char *text);

#endif
