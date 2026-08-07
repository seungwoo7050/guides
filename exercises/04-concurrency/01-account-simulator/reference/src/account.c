#include "account.h"

#include <limits.h>
#include <stddef.h>

int account_init(struct account *account, unsigned long id, long balance)
{
    if (account == NULL || balance < 0)
    {
        return -1;
    }
    account->id = id;
    account->balance = balance;
    account->initialized = 0;
    if (pthread_mutex_init(&account->mutex, NULL) != 0)
    {
        return -1;
    }
    account->initialized = 1;
    return 0;
}

static int lock_pair(
    struct account *left,
    struct account *right,
    struct account **out_first,
    struct account **out_second
)
{
    struct account *first;
    struct account *second;

    if (left == NULL || right == NULL || !left->initialized || !right->initialized)
    {
        return -1;
    }
    if (left == right)
    {
        if (pthread_mutex_lock(&left->mutex) != 0)
        {
            return -1;
        }
        *out_first = left;
        *out_second = NULL;
        return 0;
    }
    if (left->id == right->id)
    {
        return -1;
    }
    if (left->id < right->id)
    {
        first = left;
        second = right;
    }
    else
    {
        first = right;
        second = left;
    }
    if (pthread_mutex_lock(&first->mutex) != 0)
    {
        return -1;
    }
    if (pthread_mutex_lock(&second->mutex) != 0)
    {
        (void)pthread_mutex_unlock(&first->mutex);
        return -1;
    }
    *out_first = first;
    *out_second = second;
    return 0;
}

static void unlock_pair(struct account *first, struct account *second)
{
    if (second != NULL)
    {
        (void)pthread_mutex_unlock(&second->mutex);
    }
    (void)pthread_mutex_unlock(&first->mutex);
}

int account_transfer(struct account *source, struct account *destination, long amount)
{
    struct account *first;
    struct account *second;
    int result = -1;

    if (amount < 0 || lock_pair(source, destination, &first, &second) != 0)
    {
        return -1;
    }
    if (source->balance >= amount)
    {
        if (source == destination)
        {
            result = 0;
        }
        else if (destination->balance <= LONG_MAX - amount)
        {
            source->balance -= amount;
            destination->balance += amount;
            result = 0;
        }
    }
    unlock_pair(first, second);
    return result;
}

int account_get_balance(struct account *account, long *out_balance)
{
    long value;

    if (account == NULL || out_balance == NULL || !account->initialized ||
        pthread_mutex_lock(&account->mutex) != 0)
    {
        return -1;
    }
    value = account->balance;
    (void)pthread_mutex_unlock(&account->mutex);
    *out_balance = value;
    return 0;
}

int account_total(struct account *left, struct account *right, long *out_total)
{
    struct account *first;
    struct account *second;
    long total;

    if (out_total == NULL || lock_pair(left, right, &first, &second) != 0)
    {
        return -1;
    }
    if (left == right)
    {
        total = left->balance;
    }
    else if ((right->balance > 0 && left->balance > LONG_MAX - right->balance) ||
             (right->balance < 0 && left->balance < LONG_MIN - right->balance))
    {
        unlock_pair(first, second);
        return -1;
    }
    else
    {
        total = left->balance + right->balance;
    }
    unlock_pair(first, second);
    *out_total = total;
    return 0;
}

void account_destroy(struct account *account)
{
    if (account == NULL || !account->initialized)
    {
        return;
    }
    (void)pthread_mutex_destroy(&account->mutex);
    account->initialized = 0;
    account->balance = 0;
}
