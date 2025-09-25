export interface OCRResult {
  success: boolean;
  count: number;
  text: string;
  char_count: number;
  line_count: number;
  message: string;
  file_url?: string;
}
