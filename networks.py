import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torch

class SSLPretrainedNet(nn.Module):
    def __init__(self, model_path):
        efficientnetb0_new = torchvision.models.efficientnet_b0()

        # note that we need to create exactly the same backbone in order to load the weights
        backbone_new = nn.Sequential(*list(efficientnetb0_new.children())[:-1])

        ckpt = torch.load(model_path)
        backbone_new.load_state_dict(ckpt["efficientnetb0_parameters"])

        self.embeeding_net = backbone_new # load the model in a new file for inference

    def forward(self, x):
        output = self.embeeding_net(x).flatten(start_dim=1)
        return output

    def get_embedding(self, x):
        return self.forward(x)

class EmbeddingNet(nn.Module):
    def __init__(self):
        super(EmbeddingNet, self).__init__()
        self.convnet = nn.Sequential(nn.Conv2d(1, 32, 5), nn.PReLU(),
                                     nn.MaxPool2d(2, stride=2),
                                     nn.Conv2d(32, 64, 5), nn.PReLU(),
                                     nn.MaxPool2d(2, stride=2))

        self.fc = nn.Sequential(nn.Linear(64 * 4 * 4, 256),
                                nn.PReLU(),
                                nn.Linear(256, 256),
                                nn.PReLU(),
                                nn.Linear(256, 2)
                                )

    def forward(self, x):
        output = self.convnet(x)
        output = output.view(output.size()[0], -1)
        output = self.fc(output)
        return output

    def get_embedding(self, x):
        return self.forward(x)
    
class EfficientNetEmbeddingNet(nn.Module):
    def __init__(self, embedding_dim=512):
        super(EfficientNetEmbeddingNet, self).__init__()
        efficientnetb0_new = torchvision.models.efficientnet_b0()

        self.backbone = nn.Sequential(*list(efficientnetb0_new.children())[:-1])

        ckpt = torch.load("simclr_efficientnetb0_512_model.pth", map_location='cpu')  # adjust if GPU
        self.backbone.load_state_dict(ckpt["efficientnetb0_parameters"])

        self.embedding = nn.Sequential(
            nn.Flatten(),              
            nn.Linear(1280, 512),
            nn.ReLU(),
            nn.Linear(512, embedding_dim)
        )

    def forward(self, x):
        x = self.backbone(x)        
        x = self.embedding(x)     
        return x

    def get_embedding(self, x):
        return self.forward(x)


class EmbeddingNetL2(EmbeddingNet):
    def __init__(self):
        super(EmbeddingNetL2, self).__init__()

    def forward(self, x):
        output = super(EmbeddingNetL2, self).forward(x)
        output /= output.pow(2).sum(1, keepdim=True).sqrt()
        return output

    def get_embedding(self, x):
        return self.forward(x)


class ClassificationNet(nn.Module):
    def __init__(self, embedding_net, n_classes):
        super(ClassificationNet, self).__init__()
        self.embedding_net = embedding_net
        self.n_classes = n_classes
        self.nonlinear = nn.PReLU()
        self.fc1 = nn.Linear(2, n_classes)

    def forward(self, x):
        output = self.embedding_net(x)
        output = self.nonlinear(output)
        scores = F.log_softmax(self.fc1(output), dim=-1)
        return scores

    def get_embedding(self, x):
        return self.nonlinear(self.embedding_net(x))


class SiameseNet(nn.Module):
    def __init__(self, embedding_net):
        super(SiameseNet, self).__init__()
        self.embedding_net = embedding_net

    def forward(self, x1, x2):
        output1 = self.embedding_net(x1)
        output2 = self.embedding_net(x2)
        return output1, output2

    def get_embedding(self, x):
        return self.embedding_net(x)


class TripletNet(nn.Module):
    def __init__(self, embedding_net):
        super(TripletNet, self).__init__()
        self.embedding_net = embedding_net

    def forward(self, x1, x2, x3):
        output1 = self.embedding_net(x1)
        output2 = self.embedding_net(x2)
        output3 = self.embedding_net(x3)
        return output1, output2, output3

    def get_embedding(self, x):
        return self.embedding_net(x)
