#include "account.h"

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

int account_transfer(struct account *source, struct account *destination, long amount)
{
    (void)source;
    (void)destination;
    (void)amount;
    return -1;
}

int account_get_balance(struct account *account, long *out_balance)
{
    (void)account;
    (void)out_balance;
    return -1;
}

int account_total(struct account *left, struct account *right, long *out_total)
{
    (void)left;
    (void)right;
    (void)out_total;
    return -1;
}

void account_destroy(struct account *account)
{
    if (account != NULL && account->initialized)
    {
        (void)pthread_mutex_destroy(&account->mutex);
        account->initialized = 0;
    }
}
