export interface HandResult {
  success: boolean;
  hands: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
}
