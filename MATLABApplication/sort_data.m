%--------------------------------------------------------------------------

% Filename:     sort_data.m
% Adapted from: Texas Instruments
% Version:      2.00
% Edit date:    21/09/2025

%--------------------------------------------------------------------------

% Description:

% Sorts raw unsorted (int16) radar data into 3D radar data cube.

% Modification of Matlab code provided in Texas Instrumentals
% documentation which can be found at:
% https://www.ti.com/lit/an/swra581b/swra581b.pdf

%--------------------------------------------------------------------------
function data_cube = sort_data(frame_data, nSamples, nChirps, nVChannels, real_or_complex)
    % input  : frame_data -> Raw unsorted int16 radar data (vector)
    % input  : nSamples -> Number of samples
    % input  : nChirps -> Number of chirps
    % input  : nVChannels -> Number of virtual channels
    % input  : real_or_complex -> real = 0, complex = 1
    % output : data_cube  -> 3D array with dimensions [nSamples, nChirps, nVChannels]

    % Parameters
    BYTESPERSAMPLE = 2;
    total_samples  = nSamples * nChirps * nVChannels * real_or_complex;
    output_length  = total_samples / BYTESPERSAMPLE;

    % Preallocate
    data_cube = complex(zeros(output_length,1,'single'));

    % Construct complex samples (interleaved I/Q)
    data_cube(1:2:end) = single(frame_data(1:4:end)) + 1j*single(frame_data(3:4:end));
    data_cube(2:2:end) = single(frame_data(2:4:end)) + 1j*single(frame_data(4:4:end));

    % Reshape into [nSamples, nVChannels, nChirps] (column-major order in MATLAB)
    data_cube = reshape(data_cube, [nSamples, nVChannels, nChirps]);

    % Permute to [nSamples, nChirps, nVChannels] to match Python output
    data_cube = permute(data_cube, [1, 3, 2]);
end

