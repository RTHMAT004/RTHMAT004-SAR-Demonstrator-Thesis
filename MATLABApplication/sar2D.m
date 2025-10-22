%--------------------------------------------------------------------------

% Filename:     sar2D.m
% Created By:   Matthew Rathbone
% Adaptd from:  Muhammet Emin Yanik, Prof. Murat Torlak
% Version:      1.00
% Edit date:    22/10/2025

%--------------------------------------------------------------------------

% Description:

% Reconstructs a 2D Image in azimuth and elevation directions, from a single axis (1D) aperture scan. Stop-and-go method is assumed. 

%--------------------------------------------------------------------------

function [azAxis,elevAxis,sarDB] = sar2D(nSamples, nChirps, numXposition, numYposition, nFFTtime, nFFTSpace, z0, dx, dy, Fs, Slope)    
    
    rawDataFFT = zeros(p.nSamples*2, numXposition, numYposition);
    for y = 0:numYposition-1
            rawData = zeros(p.nSamples,p.nChirps,numXposition);
            fileName = sprintf('',numXposition,y);
            unordered = readFromBinFile(p,fileName);
            ordered = reshape(unordered, 256*2*128,numXposition);
        
                for x = 0:numXposition-1
                    frame = ordered(:,x+1);
                    frame = sort_data(frame, p.nSamples, p.nChirps, 1, 2);%assumes 1 frame
                    rawData(:,:,x+1) = frame;
                end

            rangeFFT = fft(flipud(rawData), nFFTtime, 1);  % flip if needed
            rangeFFT = squeeze(mean(rangeFFT, 2));        
            rawDataFFT(:,:,y+1) =  rangeFFT;
    end
      
    %% Create Matched Filter
    f = (0:nSamples-1).' * Fs / nSamples;
    rangeAxis = c * f / (2 * Slope);
    azAxis = dx * (-(numXposition-1)/2 : (numXposition-1)/2) * 1e-3;
    elevAxis = dy * (-(numYposition-1)/2 : (numYposition-1)/2) * 1e-3;

    k = 2*pi*f0/c;
    h = exp(-1i*2*k*sqrt(azAxis.^2 + rangeAxis.^2 + z0^2));

    %% Create SAR Image
    rangeBin = round(max(rangeAxis)/z0)*nSamples;
    sarData = squeeze(rawDataFFT(rangeBin,:,:));
    sarDataFFT = fft2(sarData);
    matchedFilterFFT = fft2(matchedFilter);
    sarImage = fftshift(ifft2(sarDataFFT .* h));

    sarMag = abs(sarImage);
    sarMag = sarMag ./ max(sarMag(:));       % normalize
    sarDB = 20*log10(sarMag + eps);          % convert to dB
    
    %% Plot SAR Image
    figure; mesh(yRangeT,xRangeT,flipud(sarDB)','FaceColor','interp','LineStyle','none')
    view(2)
    colormap('jet');colorbar;
    caxis([-40 0]);  
    xlabel('Azimuth bins')
    ylabel('Elevation bins')
    axis xy;
end