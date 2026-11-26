classdef NiceFiniteGroup < replab.FiniteGroup
% A nice finite group is a finite group equipped with an injective homomorphism into a permutation group
%
% Reference that triggers the error: `.eqv`

    methods

        function b = eqv(self, x, y)
            b = self.parent.eqv(x, y);
        end

    end

end
