classdef Domain
% Describes a set of elements with a common structure
%
% Those elements can be compared (`.eqv`), and random elements can be produced (`.sample`).

    methods % ABSTRACT

        function b = eqv(self, t, u)
        % Tests domain elements for equality/equivalence
        %
        % Args:
        %   t (domain element): First element to test
        %   u (domain element): Second element to test
        %
        % Returns:
        %   logical: True when ``t`` and ``u`` are equivalent, and false otherwise
            error('Abstract');
        end

    end

end
