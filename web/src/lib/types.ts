export type Label = Record<string, string>;

export type PlaceSummary = {
  slug: string;
  name: string;
  category: string | null;
  address: string | null;
  lat: number | null;
  lng: number | null;
  distance: number | null;
  operating_status: string;
};

export type AccessibilityValue = {
  criterion: string;
  label: Label;
  handicap_families: string[];
  value: { value?: unknown } & Record<string, unknown>;
};

export type TreeNode = {
  slug: string;
  label: Label;
  description?: Label;
  type: string;
  handicap_families?: string[];
  children: TreeNode[];
  value?: { value?: unknown } | null;
};

export type Photo = {
  url: string;
  credit: string | null;
  license: string | null;
};

export type Review = {
  id: number;
  rating: number;
  body: string;
  author_name: string | null;
  created: string;
  status: string;
};

export type ReviewPage = {
  items: Review[];
  total: number;
  page: number;
  size: number;
};

export type PlaceDetail = PlaceSummary & {
  accessibility: AccessibilityValue[];
  accessibility_by_family: Record<string, number>;
  tree: TreeNode[];
  filled_rate: number;
  photos: Photo[];
  rating: number | null;
  review_count: number;
};

export type User = {
  id: number;
  email: string;
  role: string;
  display_name: string | null;
  email_verified: boolean;
};

export type Category = {
  slug: string;
  name: string;
  label: Label;
};

export type CriterionNode = {
  id?: number;
  slug: string;
  label: Label;
  description: Label;
  type: string;
  handicap_families: string[];
  en17210_ref: string | null;
  children: CriterionNode[];
};
