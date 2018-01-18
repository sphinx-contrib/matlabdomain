classdef PropTypeOld
    properties
        link_name@char = 'none';
        pos@double vector = zeros(3,1);
        rotm@double matrix = zeros(3,3);
        idx@uint8 scalar = 0;
    end
end