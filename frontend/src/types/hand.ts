export interface HandResult {
  success: boolean;
  count: number;
  fingers: Array<{
    index: number;
    pos: {
      x: number;
      y: number;
    };
  }>;
  message: string;
  result_image_url?: string;
}
