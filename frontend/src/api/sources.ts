import { apiRequest } from "./client";
import type { BrandSource } from "@/types";

/** Approved guidelines and product facts, used for source chips and the source drawer. */
export const listSources = (): Promise<BrandSource[]> =>
  apiRequest<BrandSource[]>("/api/sources");
