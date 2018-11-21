classdef ClassWithLineContinuation < ...
      handle

    methods
        function obj = ClassWithLineContinuation(link_name, pos, rotm)
            obj.link_name = link_name;
            obj.pos       = pos;
            obj.rotm      = rotm;
        end
    end
end
