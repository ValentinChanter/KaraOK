'use client';

import { useState, ChangeEvent, FormEvent } from 'react';
import Image from "next/image"
  
const Home = () => {
  const [file, setFile] = useState<File | null>(null);
  const [musicLink, setMusicLink] = useState<string>('');
  const [modelFilename, setModelFilename] = useState<string>('UVR_MDXNET_KARA_2.onnx');
  const [message, setMessage] = useState<string>('');
  const [processing, setProcessing] = useState<boolean>(false);
  const [alphabet, setAlphabet] = useState<string>('kanjitokana');
  const [translation, setTranslation] = useState<string>('null');
  const [loadingProgress, setLoadingProgress] = useState<number>(0);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [audioOutput, setAudioOutput] = useState<string>('');

  const loadingBarRefreshRate = 30
  const loadingBarMs = 1000 / loadingBarRefreshRate

  const resetStates = () => {
    setProcessing(false);
    setLoadingProgress(0);
    setCurrentStep(0);
  }

  const updateLoadingProgress = (elapsedTime: number, theoricalTime: number) => {
    const newTime = Math.round(elapsedTime / theoricalTime * 100);
    if (newTime < 100) {
      setLoadingProgress(newTime);

      setTimeout(() => {
        updateLoadingProgress(elapsedTime + loadingBarMs / 1000, theoricalTime);
      }, loadingBarMs);
    }
  }

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

    const separationForm = new FormData();
    if (musicLink.length > 0) separationForm.append('musicLink', musicLink);
    else if (file) separationForm.append('file', file);
    separationForm.append('model_filename', modelFilename);

    try {
      setProcessing(true);
      setAudioOutput('');
      setCurrentStep(1);

      updateLoadingProgress(0, 8);

      const separationResponse = await fetch('/api/separate', {
        method: 'POST',
        body: separationForm,
      });

      const separationResult = await separationResponse.json();
      if (separationResponse.ok) {
        setCurrentStep(2);
        setLoadingProgress(100);

        const baseFilename = separationResult.base_filename;
        const vocalsFilename = separationResult.vocals_filename;
        const instFilename = separationResult.inst_filename;
        const audioTime = separationResult.audio_time;
        const audioDuration = separationResult.audio_duration;
        
        const transcriptionForm = new FormData();
        transcriptionForm.append('base_filename', baseFilename);
        transcriptionForm.append('vocals_filename', vocalsFilename);

        updateLoadingProgress(0, 11 * audioDuration / 20);

        const transcriptionResponse = await fetch('/api/transcribe', {
          method: 'POST',
          body: transcriptionForm,
        });

        const transcriptionResult = await transcriptionResponse.json();
        if (transcriptionResponse.ok) {
          setCurrentStep(3);
          setLoadingProgress(100);

          const transcriptionFilename = transcriptionResult.transcription;
          const transcTime = transcriptionResult.transc_time;

          const renderForm = new FormData();
          renderForm.append('alphabet', alphabet);
          renderForm.append('translation', translation);
          renderForm.append('base_filename', baseFilename);
          renderForm.append('inst_filename', instFilename);
          renderForm.append('transcription', transcriptionFilename);

          updateLoadingProgress(0, 13 * audioDuration / 20);

          const renderResponse = await fetch('/api/render', {
            method: 'POST',
            body: renderForm,
          });

          const renderResult = await renderResponse.json();
          if (renderResponse.ok) {
            setCurrentStep(0);
            setLoadingProgress(100);

            const videoPath = renderResult.video_path;
            const renderTime = renderResult.render_time;

            setAudioOutput(videoPath);
            setMessage(`Success! Audio time: ${audioTime}, Transcription time: ${transcTime}, Render time: ${renderTime}`);
            setProcessing(false);
            setLoadingProgress(0);
          } else {
            setMessage(`Error in render: ${renderResult.error}`);
            resetStates();
          }
        } else {
          setMessage(`Error in transcription: ${transcriptionResult.error}`);
          resetStates();
        }
      } else {
        setMessage(`Error in separation: ${separationResult.error}`);
        resetStates();
      }
    } catch (error) {
      setMessage('Error uploading file.');
      resetStates();
    }
  };

  return (
    <div className='relative flex min-h-screen flex-col justify-center overflow-hidden bg-gray-50 py-6'>
      <div className="absolute inset-0 bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]"></div>
      <div className='relative w-[740px] mx-auto bg-white px-6 pt-10 pb-8 shadow-xl ring-1 ring-gray-900/5 rounded-lg'>
        <div className='mx-auto text-black'>
          <a href="https://github.com/ValentinChanter/KaraOK" target="_blank" className='flex flex-row justify-center mb-8'>
            <Image src="/../public/logo.png" width={300} height={200} alt="KaraOK"/>
          </a>
            <form onSubmit={handleSubmit}>
              <div className='mx-4 shadow-md px-8 py-4 rounded-lg flex flex-row justify-between mb-2'>
                <label className='text-lg font-semibold'>1. Choose an audio file</label>
                <div className='flex flex-col'>
                  <input type="file" onChange={handleFileChange} accept=".mp3" />
                  <div className='relative flex py-1 items-center'>
                    <div className='flex-grow border-t border-gray-400'></div>
                    <span className='flex-shrink mx-4 text-gray-400'>or</span>
                    <div className='flex-grow border-t border-gray-400'></div>
                  </div>
                  <div className='flex flex-row'>
                    <div className='mr-2 flex flex-col justify-center'>
                      <label className='text-sm'>Link:</label>
                    </div>
                    <input className='border rounded-md bg-slate-100 px-2 py-1' type="text" value={musicLink} onChange={(e) => setMusicLink(e.target.value)} />
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
              <div className='mx-4 shadow-md px-8 py-4 rounded-lg flex flex-row justify-between mb-2'>
                <div className='flex flex-col'>
                  <label htmlFor="translation" className='text-lg font-semibold'>4. Choose a translation</label>
                  <p>(optional)</p>
                </div>
                <select className="p-2 rounded-md bg-slate-100 w-1/2" name="translation" id="translation" value={translation} onChange={(e) => setTranslation(e.target.value)}>
                    <option value="null">No translation</option>
                    <option value="en">English</option>
                    <option value="ja">Japanese</option>
                    <option value="fr">French</option>
                    <option value="es">Spanish</option>
                </select>
              </div>
              <div className={`mx-4 mt-6 flex flex-row justify-center rounded-full shadow-lg ${processing ? "bg-slate-500" : "bg-[#ffdc5e]"}`}>
                <button className='text-white w-full h-full py-4 text-3xl font-bold' disabled={processing}>OK!</button>
              </div>
            </form>
            <div className={`mx-4 mt-6 bg-[#fff0b4] rounded-full h-6 dark:bg-[#5e5b52]${currentStep == 0 ? " hidden" : ""}`}>
              <div className='bg-[#ffdc5e] h-6 rounded-full text-lg font-medium text-white text-center p-0.5 leading-none' style={{width: `${loadingProgress}%`}}>Step {currentStep}/3</div>
            </div>
            <div className={`mx-4 mt-6 flex flex-row justify-center rounded-full shadow-lg bg-[#ffdc5e]${audioOutput ? "" : " hidden"}`}>
              <a className='text-white w-full h-full py-4 text-3xl font-bold text-center' href={audioOutput} download>Download</a>
            </div>
            <div className={`mx-4 mt-6 flex flex-row justify-center${message ? "" : " hidden"}`}>
              <p className='w-full h-full py-4 text-md text-center'>{message}</p>
            </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
