import torch
from torch import nn

from tool.config import Configuration
from model.bev_model import BevModel
from model.bev_encoder import BevEncoder
from model.feature_fusion import FeatureFusion
from model.control_predict import ControlPredict
from model.segmentation_head import SegmentationHead
import matplotlib.pyplot as plt
import numpy as np

class ParkingModel(nn.Module):
    def __init__(self, cfg: Configuration):
        super().__init__()

        self.cfg = cfg

        self.bev_model = BevModel(self.cfg)

        self.bev_encoder = BevEncoder(self.cfg.bev_encoder_in_channel)

        self.feature_fusion = FeatureFusion(self.cfg)

        self.control_predict = ControlPredict(self.cfg)

        self.segmentation_head = SegmentationHead(self.cfg)

    def add_target_bev(self, bev_feature, target_point):
        b, c, h, w = bev_feature.shape
        bev_target = torch.zeros((b, 1, h, w), dtype=torch.float).to(self.cfg.device, non_blocking=True)

        x_pixel = (h / 2 + target_point[:, 0] / self.cfg.bev_x_bound[2]).unsqueeze(0).T.int()
        y_pixel = (w / 2 + target_point[:, 1] / self.cfg.bev_y_bound[2]).unsqueeze(0).T.int()
        target_point = torch.cat([x_pixel, y_pixel], dim=1)

        noise = (torch.rand_like(target_point, dtype=torch.float) * 10 - 5).int()
        target_point += noise

        for batch in range(b):
            bev_target_batch = bev_target[batch][0]
            target_point_batch = target_point[batch]
            bev_target_batch[target_point_batch[0] - 4:target_point_batch[0] + 4,
                             target_point_batch[1] - 4:target_point_batch[1] + 4] = 1.0

        bev_feature = torch.cat([bev_feature, bev_target], dim=1)
        return bev_feature, bev_target

    def encoder(self, data):
        images = data['image'].to(self.cfg.device, non_blocking=True)
        # print("images:", images.size())        
        intrinsics = data['intrinsics'].to(self.cfg.device, non_blocking=True)
        extrinsics = data['extrinsics'].to(self.cfg.device, non_blocking=True)
        target_point = data['target_point'].to(self.cfg.device, non_blocking=True)
        # print("target_point:", target_point.size())        
        ego_motion = data['ego_motion'].to(self.cfg.device, non_blocking=True)
        # print("ego_motion:", ego_motion.size())

        bev_feature, pred_depth = self.bev_model(images, intrinsics, extrinsics)

        bev_feature, bev_target = self.add_target_bev(bev_feature, target_point)
        # print("bev_feature:", bev_feature.size())

        # """
        # Overlay BEV target onto BEV feature and visualize.
        # """
        # bev_feature = bev_feature.detach().cpu().numpy()[0, :3]  # 取前 3 通道
        # bev_target = bev_target.detach().cpu().numpy()[0, 0]  # 取目标点

        # bev_feature = bev_feature.transpose(1, 2, 0)  # (C, H, W) -> (H, W, C)
        # # bev_feature = (bev_feature - bev_feature.min()) / (bev_feature.max() - bev_feature.min())  # 归一化

        # # 叠加目标点：将目标点区域设为红色
        # overlay = np.zeros_like(bev_feature)
        # overlay[..., 0] = bev_target  # 目标点设为红色通道 (R)
        
        # bev_with_target = np.clip(bev_feature + overlay, 0, 1)  # 避免超出范围

        # plt.imshow(bev_with_target)
        # plt.title("BEV Feature with Target Overlay")
        # plt.show()

        bev_down_sample = self.bev_encoder(bev_feature)
        # print("bev_down_sample:", bev_down_sample.size())

        fuse_feature = self.feature_fusion(bev_down_sample, ego_motion)

        pred_segmentation = self.segmentation_head(fuse_feature)

        return fuse_feature, pred_segmentation, pred_depth, bev_target

    def forward(self, data):
        fuse_feature, pred_segmentation, pred_depth, _ = self.encoder(data)
        # print("fuse_feature:", fuse_feature.size())
        # print("pred_segmentation:", pred_segmentation.size())
        # print("pred_depth:", pred_depth.size())        
        pred_control = self.control_predict(fuse_feature, data['gt_control'].cuda())
        # print("pred_control:", pred_control.size())        
        return pred_control, pred_segmentation, pred_depth

    def predict(self, data):
        fuse_feature, pred_segmentation, pred_depth, bev_target = self.encoder(data)
        pred_multi_controls = data['gt_control'].cuda()
        for i in range(3):
            pred_control = self.control_predict.predict(fuse_feature, pred_multi_controls)
            pred_multi_controls = torch.cat([pred_multi_controls, pred_control], dim=1)
        return pred_multi_controls, pred_segmentation, pred_depth, bev_target
