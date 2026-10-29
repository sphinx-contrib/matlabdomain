function out = f_with_namespaced_validator_argument(a)
    arguments
        a {x.y.z}
    end
end
