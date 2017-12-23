classdef ClassWithEvent < handle
    events
        update % An "events" block causes Sphinx to hang.
    end
end