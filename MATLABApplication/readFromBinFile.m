
%--------------------------------------------------------------------------

% Filename:     readFromBinFile.m
% Author:       William Bourn
% Adapted By:   Matthew Rathbone
% Version:      2.00
% Edit date:    21/09/2025

%--------------------------------------------------------------------------

% Description:

% Reads the binary data from a .bin file and places it into an array. The
% .bin file is created using the capture function of mmWave Studio and
% contains the raw IQ (In-phase & Quadrature) time data for the receiver of
% a DCA1000EVM and an associated AWR1642BOOST module.

% N.B.:
% Modification of Matlab code provided in Texas Instrumentals
% documentation which can be found at:
% https://www.ti.com/lit/an/swra581b/swra581b.pdf

%--------------------------------------------------------------------------

function[data] = readFromBinFile(filename,nSamples,nChirps,nFrames)
    %Function Variables
    %----------------------------------------------------------------------
    % filename (string):    Path of the .bin file to be read. Must contain
    %                       the '.bin suffix'.
    % size (int):           The size of the output array
    %----------------------------------------------------------------------
    %Determine the number of samples that need to be read from the .bin
    %file
    size = 2*nSamples*nChirps*nFrames;

    %Determine the number of data values in the file is less than the
    %length of the output array. Data is in a 16-bit format.
    if dir(filename).bytes < 2*size
        %Set the number of samples to read to the number of samples in the
        %file
        samples = dir(filename).bytes/2;
    else
        %Set the number of samples to read to the size of the output array
        samples = size;
    end
        
    %Open the file in read-only mode
    file = fopen(filename, 'r');
    
    %Read samples into the output array
    data = fread(file, samples, 'int16').';
    
    %Close the file
    fclose(file);

    %----------------------------------------------------------------------
end

%--------------------------------------------------------------------------
