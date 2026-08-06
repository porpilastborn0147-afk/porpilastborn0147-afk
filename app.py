def check_password(self, password):
    return bcrypt.check_password_hash(self.password_hash, password)