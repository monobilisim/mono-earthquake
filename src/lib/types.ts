export type UserGroup = {
  id: number;
  name: string;
  tenant: string;
};

export type Poll = {
  id: number;
  name: string;
  type: string;
  threshold: number;
};
