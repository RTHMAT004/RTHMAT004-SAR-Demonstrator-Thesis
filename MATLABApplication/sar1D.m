%--------------------------------------------------------------------------

% Filename:     sar1D.m
% Created By:   Matthew Rathbone
% Version:      2.00
% Edit date:    21/09/2025

%--------------------------------------------------------------------------

% Description:

% Reconstructs a 2D Image in range and azimuth directions, from a single axis (1D) aperture scan. Stop-and-go method is assumed. 

%--------------------------------------------------------------------------

clc; clear; close all;

nSamples = ;% Number of samples
nChirps = ; % Number of chirps
nFrames = ; % Number of frames
Fs = ; % Sampling frequency (Ms/s)
Fc = ; % Carrier frequency (Hz)
Slope = ; % Frequency slope (Hz/s)
dx = ; % Increments of sampling in x-direction (m)

for j = [4]
    fileName = '.bin';
    [folder, name, ext] = fileparts(fileName);
    rawData = zeros(nSamples,nChirps,nFrames);
    unordered = readFromBinFile(p, fileName);
    ordered = reshape(unordered, 256*2*128,nFrames);
    
    for i = 1:nFrames
        frame = ordered(:,i);
        frame = sort_data(frame, nSamples, nChirps, 1, 2); % sort_data assumes 1 frame
        rawData(:,:,i) = frame;
      
    end
    
    dataCube = flipud(rawData); % Reorder datacube based on the ReorderEnable feature of the DCA1000's config file.
    
    [sarDB, rangeAxis, x_axis] = sar_RDA(dataCube,Fs,Fc,Slope,dx);
     
    % --- Plot ---
    figure;
    imagesc(x_axis, rangeAxis, sarDB);
    xlabel('Azimuth Bin');
    ylabel('Range (m)');
    title('2D Range–Azimuth Focused Image');
    colormap jet; colorbar;
    caxis([-60 0]);  
    axis xy;

end
function [SRA_focused, rangeAxis, azAxis] = sar_RDA(cube, fs, fc, slope, dx)
    % cube: [Nsamples × Nchirps × Nframes]
    % fs: ADC sampling rate
    % fc: carrier frequency
    % slope: chirp slope (Hz/s)
    % dx: aperture step (m)
    
    c = 3e8;
    lambda = c / fc;
    [NumSamples, Nchirps, Nframes] = size(cube)
    
    Ns=512
    %% Range Compression
    rangeFFT = fft(cube_win, Ns, 1);
    SRA = squeeze(mean(rangeFFT, 2)); % Coherent Integration

    %% Create array's for range and azimuth axis depending on the waveform parameters.
    f = (0:Ns-1).' * fs / Ns;
    rangeAxis = c * f / (2 * slope);
    azAxis = dx * (-(Nframes-1)/2 : (Nframes-1)/2) * 1e-3;

    %% Azimuth FFT to spatial frequency domain
    SRD = fft(SRA, Nframes, 2);   % No windowing/padding here

    %% Create matched filter
    Rref = sqrt(rangeAxis.^2 + azAxis.^2);
    hRef = exp(-1i * 4 * pi * Rref / lambda);
    HRef = fft(hRef, Nframes, 2);
    HRef_conj = conj(HRef);  

    %% Apply matched filter
    SRD_focused = SRD .* HRef_conj;
    
    %% IFFT back to Range–Azimuth domain
    SRA_focused = fftshift(ifft(SRD_focused,740,2),2);

    %% Normalise magnitudes
    sarMag = abs(SRA_focused);
    sarMag = sarMag ./ max(sarMag(:));
    sarDB = 20*log10(sarMag + eps);
end




