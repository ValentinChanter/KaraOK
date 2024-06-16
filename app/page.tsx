'use client';

import { useState, ChangeEvent, FormEvent } from 'react';

const Home = () => {
  const [file, setFile] = useState<File | null>(null);
  const [outputFormat, setOutputFormat] = useState<string>('mp3');
  const [modelFilename, setModelFilename] = useState<string>('UVR_MDXNET_KARA_2.onnx');
  const [message, setMessage] = useState<string>('');

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!file) {
      setMessage('Please select a file to upload.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('output_format', outputFormat);
    formData.append('model_filename', modelFilename);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      if (response.ok) {
        setMessage('File successfully processed.');
      } else {
        setMessage(result.error);
      }
    } catch (error) {
      setMessage('Error uploading file.');
    }
  };

  return (
    <div>
      <h1>Audio Separator</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Choose an audio file:
          <input type="file" onChange={handleFileChange} accept=".mp3" required />
        </label>
        <br />
        <label>
          Output Format:
          <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)}>
            <option value="mp3">MP3</option>
            <option value="wav">WAV</option>
          </select>
        </label>
        <br />
        <label>
          Model Filename:
          <input
            type="text"
            value={modelFilename}
            onChange={(e) => setModelFilename(e.target.value)}
          />
        </label>
        <br />
        <button type="submit">Upload and Separate</button>
      </form>
      {message && <p>{message}</p>}
    </div>
  );
};

export default Home;