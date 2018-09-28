classdef ClassWithEventMethod

events
    update % An "events" block causes Sphinx to hang.
end

methods 
function myfunc()
end
end
end