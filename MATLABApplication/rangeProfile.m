function [spectrum, range] = rangeProfile(fileName, nSamples, nChirps, nFrames, nFFTTime, bandWidth, sampleFreq, tChirp)       
    %% Fixed parameters for all scenarios
    c = physconst('lightspeed');
    
    rawData = complex(zeros(nSamples,nChirps,nFrames)); % Creating empty array to be popuated with ordered values.
    unorderedRaw = readFromBinFile(fileName,nSamples,nChirps,nFrames);
    ordered = reshape(unorderedRaw, nSamples*nChirps*2, nFrames);
    
    for i = 1:nFrames
        frame = ordered(:,i);
        frame = sort_data(frame, nSamples, nChirps, 1, 2); % Assumes 1 frame is input.
        rawData(:,:,i) = frame;
    
        spectrum = fft(frame, nFFTTime, 1); % rawData is nSamplesxnChirps. I take the FFT along the 1st Dimension.
        spectrum = abs(spectrum); % Get magnitude
        spectrum = mean(spectrum,2); % Averaging across chirps.
    
        K = bandWidth / tChirp;           % Chirp slope [Hz/s]     
        f_b = (0 : nSamples-1)*(sampleFreq / nSamples);  % FFT bin frequencies
        range = (c * f_b) / (2*K);  % Range in meters
    end
end

