export interface FaceResult {
  success: boolean;
  count: number;
  faces: Array<{
    index: number;
    box: {
      x: number;
      y: number;
      w: number;
      h: number;
    };
    score: number;
  }>;
  message: string;
  result_image_url?: string;
}
