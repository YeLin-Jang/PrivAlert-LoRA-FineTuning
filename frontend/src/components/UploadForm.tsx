import { useState } from "react";
import { detectFace, detectHand, extractText } from "@/api";

export default function UploadForm() {
  const [result, setResult] = useState<any>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];

    const face = await detectFace(file);
    const hand = await detectHand(file);
    const ocr = await extractText(file);

    setResult({ face, hand, ocr });
  }

  return (
    <div>
      <input type="file" onChange={handleUpload} />
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </div>
  );
}
