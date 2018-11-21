classdef ClassWithMismatch

    methods
        function obj = ClassWithNameMismatch(link_name, pos, rotm)
            obj.link_name = link_name;
            obj.pos       = pos;
            obj.rotm      = rotm;
        end
    end
end
