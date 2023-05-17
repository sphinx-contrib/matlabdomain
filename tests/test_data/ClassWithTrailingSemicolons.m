classdef ClassWithTrailingSemicolons < hgsetget
    % Smoothing like it is performed withing Cxx >v7.0 (until v8.2 at least).
    % Uses constant 228p_12k frequency vector:

    properties
        m_dSmoothingWidth;                               % Smoothing Width
        m_nExtL;
        m_nExtR;
        m_dSigmaSquared;
        m_dFreqExtended;
        m_dFreqLeft;
        m_dFreqRight;
        m_dBandWidth;
    end;
    properties (Constant)
        m_dFreq = [ 100  105  110  115  120  125  130  135  145  150 ...
            160  165  175  180  190  200  210  220  230  240 ...
            250  260  275  290  300  315  330  345  360  380 ...
            400  420  440  460  480  500  525  550  575  600 ...
            630  660  700  730  760  800  830  870  900  950 ...
            1000 1050 1100 1150 1200 1250:62.5:12000];
    end;
    methods
        function obj = ClassWithTrailingSemicolons()
            % Assign smoothing width to object properties
            obj.m_dSmoothingWidth = 10.0;
        end;
        function smooth_curve = CxxSmoothing(obj, curve)
            smooth_curve = zeros(1, length(obj.m_dFreq));

        end;
        function sigma = CalculateSigma(obj)
            sigma = obj.m_dFreq;
            for i = 1:length(sigma)
                iSigma = sigma(i);
                sigma(i) = iSigma * (obj.m_dSmoothingWidth / 100);
            end;
        end;
    end;
end
