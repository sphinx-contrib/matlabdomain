function [o1, o2, o3] = f_with_input_argument_block(a1, a2)
    arguments
        a1(1,1) double = 0 % the first input
        a2(1,1) double = a1 % another input
    end
    o1 = a1; o2 = a2; o3 = a1 + a2;
    for n = 1:3
        o1 = o2;
        o2 = o3;
        o3 = o1 + o2;
    end
end
