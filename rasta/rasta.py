import os
import time
import copy
import torch
import torch.nn as nn
import torchvision.models as models
import torch.optim as optim
from torch.autograd import Variable
from tensorboardX import SummaryWriter

from PIL import Image
Image.MAX_IMAGE_PIXELS = 1000000000

from data import WikiArtDataLoader, get_classes

def train_model(model, dataloader, criterion, optimizer, scheduler, use_gpu=False, num_epochs=25, log_dir="runs/logs/cnn"):
    """ Trains model

    Args:
        model (nn.Module): model to train on
        dataloader: dataloader, with at least keys 'train' and 'valid'
        criterion: loss function, e.g. nn.CrossEntropyLoss()
        optimizer: optimizer function

    """
    since = time.time()

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    create_dir(log_dir)
    writer = SummaryWriter(log_dir=log_dir)

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch + 1, num_epochs))
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'valid']:
            print("start phase", phase)
            if phase == 'train':
                scheduler.step()
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_corrects_1 = 0
            running_corrects_3 = 0
            running_corrects_5 = 0

            # Iterate over data
            for inputs, labels in dataloader[phase]:
                if use_gpu:
                    inputs = Variable(inputs.cuda())
                    labels = Variable(labels.cuda())

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)

                    acc1, acc3, acc5 = accuracy(outputs, labels, topk=(1,3, 5))

                    # backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                # statistics
                running_loss += loss.item() * inputs.size(0)
                running_corrects_1 += acc1.data[0]
                running_corrects_3 += acc3.data[0]
                running_corrects_5 += acc5.data[0]

            epoch_loss = running_loss / len(dataloader[phase])
            epoch_acc_1 = running_corrects_1.double() / len(dataloader[phase])
            epoch_acc_3 = running_corrects_3.double() / len(dataloader[phase])
            epoch_acc_5 = running_corrects_5.double() / len(dataloader[phase])

            print('{} Loss: {:.4f} Acc@1: {:.4f} Acc@3: {:.4f} Acc@5: {:.4f}'.format(
                phase, epoch_loss, epoch_acc_1, epoch_acc_3, epoch_acc_5))

            writer.add_scalar('training/{}/loss'.format(phase), epoch_loss, epoch+1)
            writer.add_scalar('training/{}/acc@1'.format(phase), epoch_acc_1, epoch+1)
            writer.add_scalar('training/{}/acc@3'.format(phase), epoch_acc_3, epoch+1)
            writer.add_scalar('training/{}/acc@5'.format(phase), epoch_acc_5, epoch+1)
            save_checkpoint({
                'epoch': epoch + 1,
                'state_dict': model.state_dict(),
                'optimizer': optimizer.state_dict(),
            })

            # deep copy the model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())

        print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))
    writer.add_scalar('training/val/acc', best_acc, -1)

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model

def accuracy(output, target, topk=(1,)):
    """Computes the accuracy over the k top predictions for the specified values of k
    
    Taken from https://github.com/pytorch/examples/blob/master/imagenet/main.py
    """
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)

        _, pred = output.topk(maxk, 1, True, True)
        pred = pred.t()
        correct = pred.eq(target.view(1, -1).expand_as(pred))

        res = []
        for k in topk:
            correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
            res.append(correct_k.mul_(100.0 / batch_size))
        return res

def save_checkpoint(state, is_best=False, checkpoint_dir='runs/checkpoints/', filename='checkpoint.pth.tar'):
    '''
    a function to save checkpoint of the training
    :param state: {'epoch': cur_epoch + 1, 'state_dict': self.model.state_dict(),
                        'optimizer': self.optimizer.state_dict()}
    :param is_best: boolean to save the checkpoint aside if it has the best score so far
    :param filename: the name of the saved file
    '''
    create_dir(checkpoint_dir)
    torch.save(state, os.path.join(checkpoint_dir + filename))
    # if is_best:
    #     shutil.copyfile(self.args.checkpoint_dir + filename,
    #                     self.args.checkpoint_dir + 'model_best.pth.tar')

def create_dir(directory):
    """Creates a directory if it does not already exist.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

if __name__ == '__main__':
    data_path = 'data/wikiart'

    use_gpu = False
    num_workers = 4
    pin_memory = False
    if torch.cuda.is_available():
        use_gpu = True
        num_workers = 1
        pin_memory = True
        print('Using GPU')

    wikiart_loader = WikiArtDataLoader(data_path, 32, (0.8, 0.1, 0.1), random_seed=42, num_workers=num_workers, pin_memory=pin_memory)

    model = models.resnet50(pretrained=True)

    # freeze model params
    for param in model.parameters():
        param.requires_grad = False

    # replace output layer
    num_ftrs = model.fc.in_features
    num_styles = len(get_classes(data_path))
    model.fc = nn.Linear(num_ftrs, num_styles)

    if use_gpu:
        model = model.cuda()

    criterion = nn.CrossEntropyLoss()

    optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)

    exp_lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)

    model = train_model(model, wikiart_loader, criterion, optimizer, exp_lr_scheduler, use_gpu=use_gpu, num_epochs=25)
    create_dir('runs/models/') 
    torch.save({
        'state_dict': model.state_dict(),
        'optimizer': optimizer.state_dict(),
        'retrain': 'last_layer',
        'optimizer': 'sgd',
        'init_lr': 0.001,
        'momentum': 0.9,
        'steplr_size': 5,
        'steplr_gamma': 0.1,
    }, 'runs/models/resnet50_2018-12-8.pth.tar')