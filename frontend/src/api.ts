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
  const { data } = await api.post<FaceResult>("/face/detect", formData);
  return data;
}

export async function detectHand(file: File): Promise<HandResult> {
  const formData = new FormData();
  formData.append("image", file);
  const { data } = await api.post<HandResult>("/hand/detect", formData);
  return data;
}

export async function extractText(file: File): Promise<OCRResult> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<OCRResult>("/ocr/text", formData);
  return data;
}
