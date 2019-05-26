#!/usr/bin/env bash

docker-compose exec gitlab gitlab-rails r "token_digest = Gitlab::CryptoHelper.sha256 '$GITLAB_API_TOKEN'; token = PersonalAccessToken.new(user: User.where(id: 1).first, name: 'admin_api_token', token_digest: token_digest, scopes: [:api]); current_token = PersonalAccessToken.find_by(token_digest: token_digest); token.save if current_token.nil?"
