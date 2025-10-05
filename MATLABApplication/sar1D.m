function [xAxis, yAxis, sarImage] = sar1D(fileName, nSamples, nFrames, nChirps, samplingFreq, carrierFreq, nFFTTime)
    rawData = complex(zeros(nSamples,nChirps,nFrames));
    unordered = readFromBinFile(fileName, nSamples, nChirps, nFrames);
    ordered = reshape(unordered, nSamples*2*nChirps, nFrames);
    
    for i = 1:nFrames
        frame = ordered(:,i);
        frame = sort_data(frame, nSamples, nChirps, 1, 2); % sort_data assumes 1 frame
        rawData(:,:,i) = frame;
    end

    c = physconst('lightspeed');               % speed of light
    % [nSamples, nChirps, nFrames] = size(rawData);

    %% Range Compression
    % Windowing function to alter the sidelobes and mainlobe
    winRange = hamming(nSamples);
    rawData = rawData .* reshape(winRange, [nSamples,1,1]);

    % FFT along samples (fast time)
    nFFT = 2^nextpow2(nSamples);
    rangeFFT = fft(flipud(rawData), nFFT, 1);  % flip if needed
    rangeFFT = rangeFFT(1:nFFT/2,:,:);          % positive half

    % Average the chirps (2nd dimensions of the array) - coherent
    % integration
    rangeProfiles = squeeze(mean(rangeFFT, 2));

    %% Azimuth Compression
    % Apply azimuth window across frames (slow time)
    winAz = hamming(nFrames);
    rangeProfiles = rangeProfiles .* winAz.';

    % FFT across frames (cross-range)
    azFFT = fftshift(fft(rangeProfiles, nFFTTime, 2), 2);

    %% Magnitude & Normalize
    % basics of back projection based on magnitude
    sarImage = 20*log10(abs(azFFT) ./ max(abs(azFFT(:))));

    %% Axes in meters
    % Range axis
    freqRes = samplingFreq / nFFT;
    rg_axis = (0:(nFFT/2-1)) * freqRes;
    yAxis = c * rg_axis / (2 * carrierFreq);  % approximate

    xAxis = 1:nFrames; 
end
