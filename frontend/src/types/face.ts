export interface FaceResult {
  success: boolean;
  faces: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
}
