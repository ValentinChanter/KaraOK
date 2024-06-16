'use client';

import { useState, ChangeEvent, FormEvent } from 'react';

const Home = () => {
  const [file, setFile] = useState<File | null>(null);
  const [outputFormat, setOutputFormat] = useState<string>('mp3');
  const [modelFilename, setModelFilename] = useState<string>('UVR_MDXNET_KARA_2');
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
      setMessage('Processing...');
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
        // Remove timeout settings or make sure the request waits indefinitely
      });
      const result = await response.json();
      if (response.ok) {
        setMessage(`Success: ${result.message}`);
      } else {
        setMessage(`Error: ${result.error}`);
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
        <label htmlFor="model">
          Model Filename:
        </label>
        <select name="model" id="model" value={modelFilename} onChange={(e) => setModelFilename(e.target.value)}>
            <option value="UVR_MDXNET_KARA_2.onnx">Instrumental with back vocals</option>
            <option value="UVR-MDX-NET-Inst_HQ_3.onnx">Instrumental only</option>
        </select>
        <br />
        <button type="submit">Upload and Separate</button>
      </form>
      {message && <p>{message}</p>}
    </div>
  );
};

export default Home;
