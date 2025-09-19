export interface OCRResult {
  success: boolean;
  text: string;
  char_count: number;
  line_count: number;
  file_url?: string;
}
