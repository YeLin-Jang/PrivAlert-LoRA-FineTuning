import axios from "axios";
import type { FaceResult } from "@/types/face";
import type { HandResult } from "@/types/hand";
import type { OCRResult } from "@/types/ocr";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "multipart/form-data" },
});

export async function detectFace(file: File): Promise<FaceResult> {
  const formData = new FormData();
  formData.append("image", file);
  const { data } = await api.post<FaceResult>("/api/v1/face/detect", formData);
  return data;
}

export async function detectHand(file: File): Promise<HandResult> {
  const formData = new FormData();
  formData.append("image", file);
  const { data } = await api.post<HandResult>("/api/v1/hand/detect", formData);
  return data;
}

export async function extractText(file: File): Promise<OCRResult> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<OCRResult>("/api/v1/ocr/text", formData);
  return data;
}

export async function analyzeContent(
  images?: File[], 
  text?: string, 
  blurFingers: boolean = true, 
  showFaces: boolean = false
): Promise<any> {
  const formData = new FormData();
  
  if (images && images.length > 0) {
    // 여러 이미지 추가
    images.forEach(image => {
      formData.append("image", image);
    });
  }
  if (text) {
    formData.append("text", text);
  }
  formData.append("blur_fingers", blurFingers.toString());
  formData.append("show_faces", showFaces.toString());
  
  const { data } = await api.post("/api/v1/analyze/analyze", formData);
  return data;
}
