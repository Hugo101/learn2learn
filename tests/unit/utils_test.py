#!/usr/bin/env python3

import unittest
import copy
import torch
import learn2learn as l2l


def ref_clone_module(module):
    # First, create a copy of the module.
    clone = copy.deepcopy(module)

    # Second, re-write all parameters
    if hasattr(clone, '_parameters'):
        for param_key in module._parameters:
            if module._parameters[param_key] is not None:
                cloned = module._parameters[param_key].clone()
                clone._parameters[param_key] = cloned

    # Third, handle the buffers if necessary
    if hasattr(clone, '_buffers'):
        for buffer_key in module._buffers:
            if clone._buffers[buffer_key] is not None and \
                    clone._buffers[buffer_key].requires_grad:
                clone._buffers[buffer_key] = module._buffers[buffer_key].clone()

    # Then, recurse for each submodule
    if hasattr(clone, '_modules'):
        for module_key in clone._modules:
            clone._modules[module_key] = ref_clone_module(module._modules[module_key])
    return clone


class Model(torch.nn.Module):

    def __init__(self):
        super().__init__()
        self.model = torch.nn.Sequential(
            torch.nn.Linear(4, 64),
            torch.nn.Tanh(),
            torch.nn.Linear(64, 2)
        )

    def forward(self, x):
        return self.model(x)


class UtilTests(unittest.TestCase):

    def setUp(self):
        self.model = Model()
        self.loss_func = torch.nn.MSELoss()
        self.input = torch.tensor([[0., 1., 2., 3.]])

    def tearDown(self):
        pass

    def optimizer_step(self, model, gradients):
        for param, gradient in zip(model.parameters(), gradients):
            param.data.sub_(0.01 * gradient)

    def test_clone_module_basics(self):
        original_output = self.model(self.input)
        original_loss = self.loss_func(original_output, torch.tensor([[0., 0.]]))
        original_gradients = torch.autograd.grad(original_loss,
                                                 self.model.parameters(),
                                                 retain_graph=True,
                                                 create_graph=True)

        cloned_model = l2l.clone_module(self.model)
        self.optimizer_step(self.model, original_gradients)

        cloned_output = cloned_model(self.input)
        cloned_loss = self.loss_func(cloned_output, torch.tensor([[0., 0.]]))

        cloned_gradients = torch.autograd.grad(cloned_loss,
                                               cloned_model.parameters(),
                                               retain_graph=True,
                                               create_graph=True)

        self.optimizer_step(cloned_model, cloned_gradients)

        for a, b in zip(self.model.parameters(), cloned_model.parameters()):
            self.assertTrue(torch.equal(a, b))

    def test_clone_module_models(self):
        ref_models = [l2l.vision.models.OmniglotCNN(10),
                  l2l.vision.models.MiniImagenetCNN(10)]
        l2l_models = [copy.deepcopy(m) for m in ref_models]
        inputs = [torch.randn(5, 1, 28, 28), torch.randn(5, 3, 84, 84)]


        # Compute reference gradients
        ref_grads = []
        for model, X in zip(ref_models, inputs):
            for iteration in range(10):
                model.zero_grad()
                clone = ref_clone_module(model)
                out = clone(X)
                out.norm(p=2).backward()
                self.optimizer_step(model, [p.grad for p in model.parameters()])
                ref_grads.append([p.grad.clone().detach() for p in model.parameters()])

        # Compute cloned gradients
        l2l_grads = []
        for model, X in zip(l2l_models, inputs):
            for iteration in range(10):
                model.zero_grad()
                clone = l2l.clone_module(model)
                out = clone(X)
                out.norm(p=2).backward()
                self.optimizer_step(model, [p.grad for p in model.parameters()])
                l2l_grads.append([p.grad.clone().detach() for p in model.parameters()])

        # Compare gradients and model parameters
        for ref_g, l2l_g in zip(ref_grads, l2l_grads):
            for r_g, l_g in zip(ref_g, l2l_g):
                self.assertTrue(torch.equal(r_g, l_g))
        for ref_model, l2l_model in zip(ref_models, l2l_models):
            for ref_p, l2l_p in zip(ref_model.parameters(), l2l_model.parameters()):
                self.assertTrue(torch.equal(ref_p, l2l_p))

    def test_module_detach(self):
        original_output = self.model(self.input)
        original_loss = self.loss_func(original_output, torch.tensor([[0., 0.]]))

        original_gradients = torch.autograd.grad(original_loss,
                                                 self.model.parameters(),
                                                 retain_graph=True,
                                                 create_graph=True)

        l2l.detach_module(self.model)
        severed = self.model

        self.optimizer_step(self.model, original_gradients)

        severed_output = severed(self.input)
        severed_loss = self.loss_func(severed_output, torch.tensor([[0., 0.]]))

        fail = False
        try:
            severed_gradients = torch.autograd.grad(severed_loss,
                                                    severed.parameters(),
                                                    retain_graph=True,
                                                    create_graph=True)
        except Exception as e:
            fail = True

        finally:
            assert fail == True

    def test_distribution_clone(self):
        pass

    def test_distribution_detach(self):
        pass


if __name__ == '__main__':
    unittest.main()
