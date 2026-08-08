
create table inventory_item (
  id uuid primary key,
  available_quantity bigint not null,
  constraint ck_inventory_available_quantity_non_negative check (available_quantity >= 0)
);
