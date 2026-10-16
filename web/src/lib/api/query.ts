import { ApiError, type Problem } from "./client";
import type { components } from "./schema";

export type Schemas = components["schemas"];

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/** Turn an openapi-fetch result into data, or throw ApiError with the problem+json body. */
export async function unwrap<T>(call: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await call;
  if (error !== undefined || !response.ok) {
    throw new ApiError(response.status, (error ?? {}) as Problem);
  }
  return data as T;
}

/** Results of a paginated list, or the list itself for unpaginated endpoints. */
export function rows<T>(page: { results?: T[] } | T[] | undefined): T[] {
  if (!page) return [];
  return Array.isArray(page) ? page : (page.results ?? []);
}
