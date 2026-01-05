import { z } from 'zod';

export const paginationQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0)
});

export const parsePagination = (req) => {
  const parsed = paginationQuerySchema.safeParse(req.query);
  if (!parsed.success) {
    return { limit: 20, offset: 0 };
  }
  return parsed.data;
};
