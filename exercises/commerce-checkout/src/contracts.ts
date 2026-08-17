import { z } from "zod";

// [Implementation 2] Define runtime contracts for money, checkout commands, provider operations, and provider events before transport or persistence can consume them.
export const idSchema = z.string().min(1).max(128).regex(/^[A-Za-z0-9_-]+$/);
export const currencySchema = z.string().regex(/^[A-Z]{3}$/);
export const amountMinorSchema = z.number().int().nonnegative().safe();
export const idempotencyKeySchema = z.string().min(8).max(128).regex(/^[A-Za-z0-9._:-]+$/);

export const checkoutBodySchema = z.object({
  items: z.array(z.object({
    productId: idSchema,
    quantity: z.number().int().min(1).max(20)
  })).min(1).max(20)
}).strict();

export type CheckoutBody = z.infer<typeof checkoutBodySchema>;

export const dispatchBodySchema = z.object({
  limit: z.number().int().min(1).max(20).default(1)
}).strict().default({ limit: 1 });

export const providerEventSchema = z.object({
  id: idSchema,
  type: z.enum([
    "payment.succeeded",
    "payment.failed",
    "payment.canceled",
    "payment.refunded"
  ]),
  providerPaymentId: idSchema,
  occurredAt: z.string().datetime()
}).strict();

export type ProviderEvent = z.infer<typeof providerEventSchema>;
export type ProviderEventType = ProviderEvent["type"];

export const providerOperationResponseSchema = z.object({
  id: idSchema,
  providerPaymentId: idSchema,
  kind: z.enum(["create", "cancel", "refund"]),
  orderId: idSchema,
  amountMinor: amountMinorSchema,
  currency: currencySchema,
  status: z.literal("accepted"),
  createdAt: z.string().datetime()
}).strict();

export type ProviderOperationResponse = z.infer<typeof providerOperationResponseSchema>;

export type MoneyDto = { amountMinor: number; currency: string };
export type OrderItemDto = {
  productId: string;
  sku: string;
  name: string;
  unitPrice: MoneyDto;
  quantity: number;
  lineTotal: MoneyDto;
};
export type OrderDto = {
  id: string;
  status: string;
  subtotal: MoneyDto;
  total: MoneyDto;
  inventoryReleased: boolean;
  payment: {
    id: string;
    providerPaymentId: string | null;
    status: string;
  };
  items: OrderItemDto[];
  createdAt: string;
  updatedAt: string;
};
