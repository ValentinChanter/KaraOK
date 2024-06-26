'use client';

import { useState, ChangeEvent, FormEvent } from 'react';
import Image from "next/image"

const Home = () => {
  const [file, setFile] = useState<File | null>(null);
  const [musicLink, setMusicLink] = useState<string>('');
  const [modelFilename, setModelFilename] = useState<string>('UVR_MDXNET_KARA_2.onnx');
  const [message, setMessage] = useState<string>('');
  const [alphabet, setAlphabet] = useState<string>('kanjitokana');

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!file && musicLink.length === 0) {
      setMessage('Please select a file to upload.');
      return;
    }

    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    formData.append('musicLink', musicLink);
    formData.append('model_filename', modelFilename);
    formData.append('alphabet', alphabet);

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
    <div className='relative flex min-h-screen flex-col justify-center overflow-hidden bg-gray-50 py-6'>
      <div className="absolute inset-0 bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]"></div>
      <div className='relative w-[740px] mx-auto bg-white px-6 pt-10 pb-8 shadow-xl ring-1 ring-gray-900/5'>
        <div className='mx-auto text-black'>
          <a href="https://github.com/ValentinChanter/KaraOK" target="_blank" className='flex flex-row justify-center mb-8'>
            <Image src="/../public/logo.png" width={300} height={200} alt="KaraOK"/>
          </a>
            <form onSubmit={handleSubmit}>
              <div className='mx-4 shadow-md px-8 py-4 rounded-lg flex flex-row justify-between mb-2'>
                <label className='text-lg font-semibold'>1. Choose an audio file</label>
                <div className='flex flex-col'>
                  <input className='w-1/2' type="file" onChange={handleFileChange} accept=".mp3" />
                  <div className='flex flex-row'>
                    <label className='text-sm mt-2 mr-1'>Link:</label>
                    <input className='border border-black mt-1' type="text" value={musicLink} onChange={(e) => setMusicLink(e.target.value)} />
                  </div>
                </div>
              </div>
              <div className='mx-4 shadow-md px-8 py-4 rounded-lg flex flex-row justify-between mb-2'>
                <label htmlFor="model" className='text-lg font-semibold'>2. Choose an instrumental</label>
                <select className="p-2 rounded-md bg-slate-100 w-1/2" name="model" id="model" value={modelFilename} onChange={(e) => setModelFilename(e.target.value)}>
                    <option value="UVR_MDXNET_KARA_2.onnx">Instrumental with back vocals</option>
                    <option value="UVR-MDX-NET-Inst_HQ_3.onnx">Instrumental only</option>
                </select>
              </div>
              <div className='mx-4 shadow-md px-8 py-4 rounded-lg flex flex-row justify-between mb-2'>
                <div className='flex flex-col'>
                  <label htmlFor="alphabet" className='text-lg font-semibold'>3. Choose an alphabet</label>
                  <p>(for Japanese songs)</p>
                </div>
                <select className="p-2 rounded-md bg-slate-100 w-1/2" name="alphabet" id="alphabet" value={alphabet} onChange={(e) => setAlphabet(e.target.value)}>
                    <option value="kanjitokana">Kanji and kana</option>
                    <option value="romaji">Rōmaji</option>
                </select>
              </div>
              <div className='mx-4 mt-6 flex flex-row justify-center py-4'>
                <button type="submit">OK! (en vrai mettre le OK qui s'anime ici non ?)</button>
              </div>
            </form>
            <div className='mx-4 mt-6 flex flex-row justify-center py-4'>
              {message && <p className="text-sm">{message}</p>}
              (Ajouter un loader ici à la place de "Processing" pour montrer que ça charge ?)
            </div>
        </div>
      
      </div>
    </div>
  );
};

export default Home;
