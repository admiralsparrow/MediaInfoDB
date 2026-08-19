export interface FilterDefinition {
  key: string;
  label: string;
  type: "enum" | "boolean" | "text" | "number_min" | "number_max" | "range" | "date_range";
  group: "general" | "video" | "audio" | "subtitle";
  apiParam: string;
  apiParamMax?: string;
  multiplier?: number;
}
