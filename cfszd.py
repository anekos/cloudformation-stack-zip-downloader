#!/bin/python
# coding: utf-8

from collections import OrderedDict
from typing import Any, Dict, Optional
import os
import zipfile

import boto3
import humanize
import yaml


cfn_client = boto3.client('cloudformation')
s3_resource = boto3.resource('s3')


def represent_odict(dumper: Any, instance: Dict[Any, Any]) -> Any:
    return dumper.represent_mapping('tag:yaml.org,2002:map', instance.items())


yaml.add_representer(OrderedDict, represent_odict)


def get_stack_template(stack_name: str) -> Any:
    r = cfn_client.get_template(StackName=stack_name)
    if 'TemplateBody' not in r:
        raise Exception('Stack not found')
    body = r['TemplateBody']
    return body


def extract_s3_object(res: Any) -> Optional[Any]:
    if res['Type'] == 'AWS::Lambda::Function':
        c = res['Properties']['Code']
        return s3_resource.Bucket(c['S3Bucket']).Object(c['S3Key'])
    if res['Type'] == 'AWS::Lambda::LayerVersion':
        c = res['Properties']['Content']
        return s3_resource.Bucket(c['S3Bucket']).Object(c['S3Key'])
    return None


class App:
    def template(self, stack_name: str) -> None:
        template = get_stack_template(stack_name)
        print(yaml.dump(template))

    def download(self, stack_name: str, download_to: str) -> None:
        template = get_stack_template(stack_name)

        os.makedirs(download_to, exist_ok=True)

        for name, res in template['Resources'].items():
            s3_obj = extract_s3_object(res)
            if s3_obj is None:
                continue

            print('Download: {}'.format(name))
            filepath = os.path.join(download_to, name + '.zip')
            s3_obj.download_file(filepath)
            total_size = 0
            with zipfile.ZipFile(filepath) as z:
                for x in z.infolist():
                    total_size += x.file_size
            print('  Total: {} bytes'.format(humanize.naturalsize(total_size, gnu=True)))


if __name__ == '__main__':
    import fire
    fire.Fire(App)
