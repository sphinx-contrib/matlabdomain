function [o1, o2, o3] = f_with_output_argument_block(a1, a2)
    arguments(Output)
        o1(1,1) double % Output one
        o2(1,:) double % Another output
        o3(1,1) double {mustBePositive} % A third output
    end
    o1 = a1; o2 = a2; o3 = a1 + a2;
    for n = 1:3
        o1 = o2;
        o2 = o3;
        o3 = o1 + o2;
    end
end
